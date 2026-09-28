"""Normalize a single CSV, JSON, or XML transaction export for the pipeline."""
import csv
import io
import json
import re
import xml.etree.ElementTree as ET


TXID_KEYS = {"txid", "transactionid", "hash", "id"}
TIME_KEYS = {"timestamp", "time", "date", "datetime", "blocktime", "firstseen"}
INPUT_KEYS = {"inputs", "input", "inputaddresses", "inputaddress", "from", "fromaddress", "sender", "source", "sourceaddress", "vin", "vins"}
OUTPUT_KEYS = {"outputs", "output", "outputaddresses", "outputaddress", "to", "toaddress", "recipient", "recipients", "destination", "target", "vout", "vouts"}
ADDRESS_KEYS = {"address", "addressid", "addr", "scriptpubkeyaddress"}
AMOUNT_KEYS = {"amounts", "amount", "value", "values"}
FEE_KEYS = {"fee", "transactionfee"}


def _key(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _xml_value(element):
    result = dict(element.attrib)
    for child in element:
        value = _xml_value(child)
        key = child.tag.rsplit("}", 1)[-1]
        if key in result:
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(value)
        else:
            result[key] = value
    text = (element.text or "").strip()
    if result:
        if text:
            result["text"] = text
        return result
    return text


def _xml_records(raw):
    root = ET.fromstring(raw)
    transaction_tags = {"transaction", "tx", "record"}
    records = [node for node in root.iter() if node is not root and node.tag.rsplit("}", 1)[-1].lower() in transaction_tags]
    if root.tag.rsplit("}", 1)[-1].lower() in transaction_tags:
        records = [root]
    if not records:
        records = list(root)
    return [_xml_value(record) for record in records if list(record) or record.attrib]


def _json_records(value):
    if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
        return value
    if isinstance(value, dict):
        for name in ("transactions", "transaction", "records", "data", "results"):
            for key, child in value.items():
                if _key(key) == name:
                    try:
                        return _json_records(child)
                    except ValueError:
                        pass
    raise ValueError("JSON must contain an array of transaction records")


def _read_records(filename, raw):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension == "csv":
        records = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    elif extension == "json":
        records = _json_records(json.loads(raw.decode("utf-8-sig")))
    elif extension == "xml":
        records = _xml_records(raw)
    else:
        raise ValueError("Upload a CSV, JSON, or XML file")
    if not records:
        raise ValueError("The file contains no transaction records")
    return records


def _field(record, aliases):
    if not isinstance(record, dict):
        return None
    for key, value in record.items():
        if _key(key) in aliases and value not in (None, ""):
            return value
    for value in record.values():
        if isinstance(value, dict):
            found = _field(value, aliases)
            if found is not None:
                return found
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    found = _field(item, aliases)
                    if found is not None:
                        return found
    return None


def _sequence(value):
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text[:1] in "[{\"":
            try:
                return _sequence(json.loads(text))
            except json.JSONDecodeError:
                pass
        return [part.strip() for part in re.split(r"[;|,]", text) if part.strip()]
    return value if isinstance(value, list) else [value]


def _addresses(value):
    found = []
    for item in _sequence(value):
        if isinstance(item, dict):
            address = _field(item, ADDRESS_KEYS)
            if address is not None:
                found.extend(_addresses(address))
            else:
                for nested_value in item.values():
                    found.extend(_addresses(nested_value))
        elif item is not None and str(item).strip():
            found.append(str(item).strip())
    return list(dict.fromkeys(found))


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _cluster_addresses(transactions):
    parent = {}

    def find(address):
        parent.setdefault(address, address)
        if parent[address] != address:
            parent[address] = find(parent[address])
        return parent[address]

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    for transaction in transactions:
        inputs = transaction["input_addresses"]
        addresses = inputs + transaction["output_addresses"]
        for address in addresses:
            find(address)
        for address in inputs[1:]:
            union(inputs[0], address)

    clusters = {}
    for address in parent:
        clusters.setdefault(find(address), []).append(address)
    ordered = sorted(clusters.values(), key=lambda addresses: min(addresses))
    address_entities = {}
    entities = []
    for index, addresses in enumerate(ordered, start=1):
        entity_id = f"entity_{index:06d}"
        entities.append({"entity_id": entity_id, "label": "unknown"})
        for address in addresses:
            address_entities[address] = entity_id
    return entities, address_entities


def _csv_bytes(fieldnames, rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def normalize_dataset(filename, raw):
    """Return canonical pipeline CSV bytes and the number of inferred entities."""
    records = _read_records(filename, raw)
    transactions = []
    for index, record in enumerate(records, start=1):
        inputs = _addresses(_field(record, INPUT_KEYS))
        outputs = _addresses(_field(record, OUTPUT_KEYS))
        if not inputs and not outputs:
            continue
        txid = _field(record, TXID_KEYS) or f"transaction_{index:06d}"
        timestamp = _field(record, TIME_KEYS) or "1970-01-01T00:00:00Z"
        amounts = [_number(value) for value in _sequence(_field(record, AMOUNT_KEYS))]
        amounts = (amounts + [0.0] * len(outputs))[:len(outputs)]
        transactions.append({
            "txid": str(txid),
            "timestamp": str(timestamp),
            "input_addresses": inputs,
            "output_addresses": outputs,
            "amounts": amounts,
            "fee": _number(_field(record, FEE_KEYS)),
        })

    if not transactions:
        raise ValueError("No transaction records with recognizable input or output addresses were found")

    entities, address_entities = _cluster_addresses(transactions)
    first_seen = {}
    for transaction in transactions:
        for address in transaction["input_addresses"] + transaction["output_addresses"]:
            first_seen[address] = min(first_seen.get(address, transaction["timestamp"]), transaction["timestamp"])
    addresses = [
        {"address_id": address, "entity_id": entity_id, "first_seen": first_seen[address]}
        for address, entity_id in sorted(address_entities.items())
    ]
    transaction_rows = [
        {
            **transaction,
            "input_addresses": json.dumps(transaction["input_addresses"]),
            "output_addresses": json.dumps(transaction["output_addresses"]),
            "amounts": json.dumps(transaction["amounts"]),
        }
        for transaction in transactions
    ]

    return {
        "entities.csv": _csv_bytes(["entity_id", "label"], entities),
        "addresses.csv": _csv_bytes(["address_id", "entity_id", "first_seen"], addresses),
        "transactions.csv": _csv_bytes(
            ["txid", "timestamp", "input_addresses", "output_addresses", "amounts", "fee"],
            transaction_rows,
        ),
    }, len(entities)