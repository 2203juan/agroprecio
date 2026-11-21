import { useEffect, useState } from "react";
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const API = "/api";

const LABELS = {
  sube: { text: "Sube", className: "tag sube" },
  baja: { text: "Baja", className: "tag baja" },
  estable: { text: "Estable", className: "tag estable" },
};

const pesos = (n) => "$" + Math.round(n).toLocaleString("es-CO");
const pct = (n) => (n > 0 ? "+" : "") + (n * 100).toFixed(1) + "%";

async function getJson(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

export default function App() {
  const [alerts, setAlerts] = useState([]);
  const [bulletin, setBulletin] = useState(null);
  const [model, setModel] = useState(null);
  const [monitoring, setMonitoring] = useState(null);
  const [product, setProduct] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([getJson("/alertas"), getJson("/boletin"), getJson("/modelo"), getJson("/monitoreo")])
      .then(([a, b, m, mon]) => {
        setAlerts(a);
        setBulletin(b);
        setModel(m.produccion);
        setMonitoring(mon);
        if (a.length) setProduct(a[0].producto);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!product) return;
    getJson(`/historico/${encodeURIComponent(product)}?semanas=52`)
      .then((rows) => setHistory(rows.map((r) => ({ ...r, semana: r.semana_inicio.slice(0, 10) }))))
      .catch((e) => setError(e.message));
  }, [product]);

  if (error) return <main className="page"><p className="error">No se pudo cargar la API ({error}).</p></main>;
  if (!alerts.length) return <main className="page"><p>Cargando…</p></main>;

  const week = alerts[0].semana_inicio.slice(0, 10);
  const count = (c) => alerts.filter((a) => a.prediccion === c).length;
  const metrics = model?.metricas;
  const status = monitoring?.estado?.[0];
  const qualityOk = monitoring?.calidad?.filter((q) => q.ok).length ?? 0;
  const qualityTotal = monitoring?.calidad?.length ?? 0;

  return (
    <main className="page">
      <header>
        <div>
          <h1>AgroPrecio</h1>
          <p className="muted">Precios mayoristas de Cavasa (Cali) · semana del {week}</p>
        </div>
        <p className="muted small">Fuente: SIPSA – DANE</p>
      </header>

      <section className="tiles">
        <Tile label="Comprar ya" value={count("sube")} hint="productos que se espera que suban" />
        <Tile label="Esperar" value={count("baja")} hint="productos que se espera que bajen" />
        <Tile label="Estables" value={count("estable")} hint="sin cambio importante" />
        <Tile
          label="Ahorro simulado"
          value={metrics ? pct(metrics.modelo.ahorro_simulado) : "–"}
          hint="en el periodo de prueba"
        />
      </section>

      <section className="grid">
        <div className="card">
          <h2>Recomendaciones de la semana</h2>
          <table>
            <thead>
              <tr><th>Producto</th><th>Precio/kg</th><th>Últ. semana</th><th>Próxima</th><th>Acción</th></tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr
                  key={a.producto}
                  className={a.producto === product ? "selected" : ""}
                  onClick={() => setProduct(a.producto)}
                >
                  <td>{a.producto}</td>
                  <td>{pesos(a.precio)}</td>
                  <td className={a.cambio_1s > 0 ? "up" : "down"}>{pct(a.cambio_1s)}</td>
                  <td><span className={LABELS[a.prediccion].className}>{LABELS[a.prediccion].text}</span></td>
                  <td className="small">{a.accion} <span className="muted">({Math.round(a.confianza * 100)}%)</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="side">
          <div className="card">
            <h2>Boletín para tu restaurante</h2>
            <p className="bulletin">{bulletin?.texto}</p>
            <p className="muted small">Generado con {bulletin?.fuente === "claude" ? "Claude" : "plantilla"}</p>
          </div>

          <div className="card">
            <h2>{product}: último año</h2>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={history} margin={{ left: 8, right: 8 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="semana" tick={{ fontSize: 11 }} minTickGap={40} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => "$" + v / 1000 + "k"} width={48} />
                <Tooltip formatter={(v) => pesos(v)} />
                <Legend />
                <Line type="monotone" dataKey="precio" name="Cavasa" stroke="var(--accent)" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="precio_nacional" name="Mediana nacional" stroke="var(--muted)" dot={false} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="card">
        <h2>Estado del modelo y de los datos</h2>
        <div className="tiles">
          <Tile label="Modelo en producción" value={model?.version ?? "–"} hint={model?.fecha?.slice(0, 10)} />
          <Tile
            label="F1 modelo vs baseline"
            value={metrics ? `${metrics.modelo.f1_macro.toFixed(2)} / ${metrics.baseline_persistencia.f1_macro.toFixed(2)}` : "–"}
            hint="baseline: repetir la última semana"
          />
          <Tile
            label="Acierto últimas 8 semanas"
            value={status?.accuracy_ultimas_8_semanas != null ? pct(status.accuracy_ultimas_8_semanas).replace("+", "") : "–"}
            hint={status?.requiere_reentrenar ? "se reentrena con la próxima carga" : "dentro del umbral"}
          />
          <Tile label="Reglas de calidad" value={`${qualityOk}/${qualityTotal}`} hint={`${status?.productos_con_drift ?? 0} productos con drift`} />
        </div>
      </section>
    </main>
  );
}

function Tile({ label, value, hint }) {
  return (
    <div className="tile">
      <p className="muted small">{label}</p>
      <p className="value">{value}</p>
      {hint && <p className="muted small">{hint}</p>}
    </div>
  );
}
