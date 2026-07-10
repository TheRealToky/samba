import { ReactNode, useEffect, useState } from "react";
import { IUCN_LABEL, speciesMeta, speciesPhotoUrl, statusKey } from "../lib/species";
import { IconTrendDown, IconTrendFlat, IconTrendUp, TaxonIcon } from "./icons";

type Accent = "green" | "amber" | "water" | "violet" | "danger";

const TREND_ICON = {
  up: <IconTrendUp size={13} />,
  down: <IconTrendDown size={13} />,
  flat: <IconTrendFlat size={13} />,
};

export function Kpi({
  icon,
  label,
  value,
  unit,
  hint,
  accent = "green",
  trend,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: ReactNode;
  accent?: Accent;
  trend?: { dir: "up" | "down" | "flat"; text: string };
}) {
  return (
    <div className={`kpi a-${accent}`}>
      <div className="kpi-head">
        <span className="kpi-icon">{icon}</span>
        <span className="label">{label}</span>
      </div>
      <div className="value">
        {value}
        {unit && <span className="unit"> {unit}</span>}
      </div>
      {trend ? (
        <div className={`trend ${trend.dir}`}>
          {TREND_ICON[trend.dir]} {trend.text}
        </div>
      ) : (
        hint && <div className="hint">{hint}</div>
      )}
    </div>
  );
}

export function PanelHead({ title, sub, action }: { title: string; sub?: string; action?: ReactNode }) {
  return (
    <div className="panel-head">
      <div>
        <h2>{title}</h2>
        {sub && <div className="sub">{sub}</div>}
      </div>
      {action}
    </div>
  );
}

export function StatusChip({ status, title }: { status: string | null | undefined; title?: boolean }) {
  const key = statusKey(status);
  return (
    <span className={`chip iucn iucn-${key}`} title={IUCN_LABEL[key]}>
      {title ? IUCN_LABEL[key] : key}
    </span>
  );
}

/** Photo tile that best-effort loads a real iNaturalist photo and falls back to
 *  a flat taxon-coloured icon tile so the gallery always looks intentional. */
export function SpeciesPhoto({
  name,
  status,
  endemic,
  height = 128,
}: {
  name: string;
  status?: string | null;
  endemic?: boolean;
  height?: number;
}) {
  const meta = speciesMeta(name);
  const [photo, setPhoto] = useState<string | null>(null);

  useEffect(() => {
    let ok = true;
    speciesPhotoUrl(name).then((url) => ok && setPhoto(url));
    return () => {
      ok = false;
    };
  }, [name]);

  const style: React.CSSProperties = photo
    ? { backgroundImage: `url(${photo})`, height }
    : { background: meta.tile.bg, height };

  return (
    <div className="species-photo" style={style}>
      {!photo && (
        <span style={{ color: meta.tile.fg }}>
          <TaxonIcon group={meta.group} size={36} />
        </span>
      )}
      {endemic && <span className="chip chip-endemic endemic-abs">Endemic</span>}
      {status != null && (
        <span className="status-abs">
          <StatusChip status={status} />
        </span>
      )}
    </div>
  );
}
