import axios from "axios";

const client = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "/api" });

export const getOverview = () => client.get("/overview").then((r) => r.data);

export const getAlerts = (params = {}) =>
  client.get("/alerts", { params }).then((r) => r.data);

export const getEntity = (entityId) =>
  client.get(`/entities/${entityId}`).then((r) => r.data);

export const getEntityGraph = (entityId, hops = 2) =>
  client.get(`/graph/${entityId}`, { params: { hops } }).then((r) => r.data);

export const submitFeedback = (entityId, status) =>
  client.post("/feedback", { entity_id: entityId, status }).then((r) => r.data);

export const getDatasetSchema = () => client.get("/dataset/schema").then((r) => r.data);

export const getDatasetStatus = () => client.get("/dataset/status").then((r) => r.data);

export const uploadDataset = (file) => {
  const form = new FormData();
  form.append("file", file);
  return client.post("/dataset/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data);
};

export const searchTransactions = (q, limit = 50) =>
  client.get("/transactions/search", { params: { q, limit } }).then((r) => r.data);

export const getTransaction = (txid) =>
  client.get(`/transactions/${txid}`).then((r) => r.data);

export default client;
