import { useEffect, useRef } from "react";
import * as d3 from "d3";

const COLORS = {
  address_focus: "#f87171",
  address: "#38bdf8",
  tx: "#a78bfa",
};

export default function EvidenceGraph({ graph, width = 640, height = 380 }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!graph || !graph.nodes?.length) return;

    const nodes = graph.nodes.map((n) => ({ ...n }));
    const links = graph.edges.map((e) => ({ ...e, source: e.source, target: e.target }));

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg.append("g");

    svg.call(
      d3.zoom().scaleExtent([0.3, 4]).on("zoom", (event) => {
        g.attr("transform", event.transform);
      })
    );

    const simulation = d3
      .forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((d) => d.id).distance(50).strength(0.4))
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide(14));

    const link = g
      .append("g")
      .attr("stroke", "#334155")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", 1);

    const node = g
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => (d.is_focus ? 8 : d.kind === "tx" ? 5 : 6))
      .attr("fill", (d) => (d.is_focus ? COLORS.address_focus : d.kind === "tx" ? COLORS.tx : COLORS.address))
      .attr("stroke", "#0f172a")
      .attr("stroke-width", 1.5)
      .call(
        d3
          .drag()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    node.append("title").text((d) => `${d.id}\n${d.kind}${d.is_focus ? " (this entity)" : ""}`);

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);
      node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
    });

    return () => simulation.stop();
  }, [graph, width, height]);

  return (
    <div>
      <svg ref={svgRef} width={width} height={height} className="w-full bg-slate-900/50 rounded-lg border border-slate-800" />
      <div className="flex gap-4 text-xs text-slate-500 mt-2">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: COLORS.address_focus }} /> this entity's address
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: COLORS.address }} /> counterparty address
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: COLORS.tx }} /> transaction
        </span>
        <span className="ml-auto">scroll to zoom · drag nodes</span>
      </div>
    </div>
  );
}
