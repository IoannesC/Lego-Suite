import { useState, useEffect } from "react";
import { call } from "@decky/api";
import { PanelSection } from "@decky/ui";
import t from "../i18n/i18n";

interface SystemResources {
  cpu: number | null;
  gpu: number | null;
  ram: number | null;
}

const getResourceColor = (val: number | null) => {
  if (val === null) return "#38bdf8";
  if (val < 60) return "#38bdf8";
  if (val < 85) return "#facc15";
  return "#ef4444";
};

const getResourceBg = (val: number | null) => {
  if (val === null) return "rgba(56, 189, 248, 0.12)";
  if (val < 60) return "rgba(56, 189, 248, 0.12)";
  if (val < 85) return "rgba(250, 204, 21, 0.12)";
  return "rgba(239, 68, 68, 0.15)";
};

const ChipIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
    <rect x="4" y="4" width="8" height="8" rx="1.5" fill="#38bdf8" stroke="#9ca3af" strokeWidth="1" />
    <line x1="5" y1="1" x2="5" y2="3" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="8" y1="1" x2="8" y2="3" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="11" y1="1" x2="11" y2="3" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="5" y1="13" x2="5" y2="15" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="8" y1="13" x2="8" y2="15" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="11" y1="13" x2="11" y2="15" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="1" y1="5" x2="3" y2="5" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="1" y1="8" x2="3" y2="8" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="1" y1="11" x2="3" y2="11" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="13" y1="5" x2="15" y2="5" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="13" y1="8" x2="15" y2="8" stroke="#9ca3af" strokeWidth="1.2" />
    <line x1="13" y1="11" x2="15" y2="11" stroke="#9ca3af" strokeWidth="1.2" />
  </svg>
);

const RamIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
    <rect x="1" y="4" width="14" height="7" rx="1" fill="#1e293b" stroke="#9ca3af" strokeWidth="1" />
    <rect x="3" y="6" width="2" height="3" fill="#38bdf8" />
    <rect x="7" y="6" width="2" height="3" fill="#38bdf8" />
    <rect x="11" y="6" width="2" height="3" fill="#38bdf8" />
    <line x1="2" y1="12" x2="2" y2="13.5" stroke="#facc15" strokeWidth="1.2" />
    <line x1="4" y1="12" x2="4" y2="13.5" stroke="#facc15" strokeWidth="1.2" />
    <line x1="6" y1="12" x2="6" y2="13.5" stroke="#facc15" strokeWidth="1.2" />
    <line x1="9" y1="12" x2="9" y2="13.5" stroke="#facc15" strokeWidth="1.2" />
    <line x1="11" y1="12" x2="11" y2="13.5" stroke="#facc15" strokeWidth="1.2" />
    <line x1="13" y1="12" x2="13" y2="13.5" stroke="#facc15" strokeWidth="1.2" />
  </svg>
);

const ResourceBadge = ({
  label,
  value,
  icon,
}: {
  label: string;
  value: number | null;
  icon: JSX.Element;
}) => (
  <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
    {icon}
    <span style={{ fontWeight: 700, fontSize: "11px", color: "#9ca3af" }}>
      {label}:
    </span>
    <span
      style={{
        fontWeight: 800,
        fontSize: "11px",
        color: getResourceColor(value),
        backgroundColor: getResourceBg(value),
        padding: "2px 6px",
        borderRadius: "5px",
      }}
    >
      {value !== null ? `${Math.round(value)}%` : "-- %"}
    </span>
  </div>
);

const ResourceMonitor = () => {
  const [resources, setResources] = useState<SystemResources>({
    cpu: null,
    gpu: null,
    ram: null,
  });

  useEffect(() => {
    let mounted = true;
    const fetchResources = () => {
      try {
        call("get_system_resources")
          .then((res: any) => {
            if (mounted && res && typeof res === "object") {
              setResources({
                cpu: res.cpu !== null && res.cpu !== undefined ? Number(res.cpu) : null,
                gpu: res.gpu !== null && res.gpu !== undefined ? Number(res.gpu) : null,
                ram: res.ram !== null && res.ram !== undefined ? Number(res.ram) : null,
              });
            }
          })
          .catch((err: any) => console.error("get_system_resources error:", err));
      } catch (e) {
        console.error("fetchResources error:", e);
      }
    };

    fetchResources();
    const interval = setInterval(fetchResources, 2000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <PanelSection>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          width: "100%",
          padding: "8px 10px",
          backgroundColor: "rgba(255, 255, 255, 0.06)",
          borderRadius: "6px",
          boxSizing: "border-box",
        }}
      >
        <ResourceBadge label="CPU" value={resources.cpu} icon={<ChipIcon />} />
        <ResourceBadge label="GPU" value={resources.gpu} icon={<ChipIcon />} />
        <ResourceBadge label="RAM" value={resources.ram} icon={<RamIcon />} />
      </div>
    </PanelSection>
  );
};

export default ResourceMonitor;
