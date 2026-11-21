import { useEffect, useRef, useState } from "react";
import {
  Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const API = "/api";

// Qué hacer según la predicción para la próxima semana
const ACTION = {
  sube: { text: "Compra ya", hint: "se espera que suba", className: "chip sube" },
  baja: { text: "Espera", hint: "se espera que baje", className: "chip baja" },
  estable: { text: "Normal", hint: "sin cambio importante", className: "chip estable" },
};

const ICONS = {
  "Aguacate papelillo": "🥑", "Ahuyama": "🎃", "Cebolla cabezona blanca bogotana": "🧅",
  "Cebolla junca Aquitania": "🌱", "Cilantro": "🌿", "Habichuela": "🫛", "Lechuga Batavia": "🥬",
  "Limón Tahití": "🍋", "Lulo": "🍊", "Mango Tommy": "🥭", "Maracuyá": "🍈",
  "Mora de Castilla": "🫐", "Papa capira": "🥔", "Papa parda pastusa": "🥔", "Pimentón": "🫑",
  "Plátano hartón verde": "🍌", "Tomate chonto": "🍅", "Tomate de árbol": "🍅",
  "Yuca ICA": "🍠", "Zanahoria bogotana": "🥕",
};

const EXAMPLE_LIST = [
  ["Tomate chonto", 15], ["Cebolla cabezona blanca bogotana", 10], ["Papa parda pastusa", 25],
  ["Plátano hartón verde", 12], ["Zanahoria bogotana", 6], ["Habichuela", 4],
  ["Cilantro", 2], ["Limón Tahití", 5],
].map(([producto, kg_semana]) => ({ producto, kg_semana }));

const pesos = (n) => "$" + Math.round(n).toLocaleString("es-CO");
const pct = (n) => Math.round(Math.abs(n) * 100) + "%";
const day = (d, opts = { day: "numeric", month: "short" }) =>
  new Date(d.slice(0, 10) + "T12:00:00").toLocaleDateString("es-CO", opts);
const addDays = (d, n) => {
  const x = new Date(d.slice(0, 10) + "T12:00:00");
  x.setDate(x.getDate() + n);
  return x.toISOString().slice(0, 10);
};

async function api(path, options) {
  const res = await fetch(API + path, options);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

export default function App() {
  const [alerts, setAlerts] = useState([]);
  const [bulletin, setBulletin] = useState(null);
  const [model, setModel] = useState(null);
  const [list, setList] = useState(null);
  const [product, setProduct] = useState(null);
  const [error, setError] = useState(null);

  const load = () =>
    Promise.all([api("/alertas"), api("/boletin"), api("/modelo"), api("/lista")])
      .then(([a, b, m, l]) => {
        setAlerts(a);
        setBulletin(b);
        setModel(m.produccion);
        setList(l);
        setProduct((p) => p ?? a[0]?.producto);
        return a;
      })
      .catch((e) => setError(e.message));

  useEffect(() => { load(); }, []);

  if (error) return <Shell><p className="error">No se pudo conectar con la API ({error}).</p></Shell>;
  if (!alerts.length || !list) return <Shell><p className="muted">Cargando precios…</p></Shell>;

  const week = alerts[0].semana_inicio;
  const byProduct = Object.fromEntries(alerts.map((a) => [a.producto, a]));

  return (
    <Shell>
      <UpdateBar week={week} onDone={load} />

      <section className="layout">
        <ShoppingList list={list} setList={setList} byProduct={byProduct} onPick={setProduct} />
        <aside className="side">
          <Totals totals={list.totales} hasItems={list.items.length > 0} />
          <Bulletin bulletin={bulletin} />
        </aside>
      </section>

      <Board alerts={alerts} week={week} selected={product} onPick={setProduct} />
      {product && <ProductDetail alert={byProduct[product]} />}

      <PhotoBand />
      <footer className="muted small">
        Precios mayoristas de la central Cavasa (Cali) publicados por el SIPSA – DANE, en pesos por kilo.
        Las proyecciones son estimaciones{model ? ` del modelo ${model.version}` : ""}: el precio real puede cambiar.
      </footer>
    </Shell>
  );
}

const FLAG_COLORS = ["naranja", "turquesa", "maiz", "rosa", "hoja", "morado"];

// Banderines de plaza de mercado
function Bunting() {
  return (
    <div className="bunting" aria-hidden="true">
      {Array.from({ length: 60 }, (_, i) => <span key={i} className={FLAG_COLORS[i % FLAG_COLORS.length]} />)}
    </div>
  );
}

function Shell({ children }) {
  return (
    <>
      <header className="hero">
        <Bunting />
        <div className="hero-content">
          <div className="sign">
            <h1>AgroPrecio</h1>
            <p>Qué comprar esta semana en Cavasa</p>
          </div>
          <p className="tagline">Precios de la plaza para tu cocina · Cali</p>
          <p className="hero-text">
            Cada semana leemos el boletín de precios mayoristas del DANE y te decimos qué conviene comprar ya,
            qué puedes esperar y cuánto te va a costar el mercado.
          </p>
        </div>
      </header>
      <main className="page">{children}</main>
    </>
  );
}

function PhotoBand() {
  return (
    <section className="band">
      <Bunting />
      <div className="band-content">
        <p className="band-title">De la plaza a tu cocina</p>
        <p>Frutas, verduras y tubérculos de Cavasa, con precios que se actualizan cada semana.</p>
      </div>
    </section>
  );
}

// ---------- Actualización con el boletín nuevo del DANE ----------

function UpdateBar({ week, onDone }) {
  const [job, setJob] = useState(null);
  const [message, setMessage] = useState(null);
  const timer = useRef(null);

  const poll = (weekBefore) => {
    timer.current = setTimeout(async () => {
      const s = await api("/actualizar");
      setJob(s);
      if (s.corriendo) return poll(weekBefore);
      if (s.codigo !== 0) return setMessage({ ok: false, text: "La actualización falló. Revisa logs/actualizacion.log." });
      const fresh = await onDone();
      const newWeek = fresh?.[0]?.semana_inicio;
      setMessage(newWeek && newWeek !== weekBefore
        ? { ok: true, text: `¡Llegó el boletín nuevo! Ya ves la semana del ${day(newWeek)}.` }
        : { ok: true, text: "Todavía no hay boletín nuevo del DANE. Los precios siguen siendo los más recientes." });
    }, 2000);
  };

  useEffect(() => {
    // Si ya había una actualización corriendo (por ejemplo la automática), la seguimos
    api("/actualizar").then((s) => { setJob(s); if (s.corriendo) poll(week); }).catch(() => {});
    return () => clearTimeout(timer.current);
  }, []);

  const start = async () => {
    setMessage(null);
    setJob(await api("/actualizar", { method: "POST" }));
    poll(week);
  };

  const running = job?.corriendo;
  const lastLine = job?.ultimas_lineas?.at(-1)?.replace(/^\S+ \S+ \w+ /, "");

  return (
    <section className="update">
      <div>
        <p className="week">
          Precios de la semana del <strong>{day(week)}</strong> al <strong>{day(addDays(week, 6), { day: "numeric", month: "short", year: "numeric" })}</strong>
        </p>
        <p className="muted small">
          {running ? `Buscando en el DANE… ${lastLine ?? ""}`
            : message ? <span className={message.ok ? "ok" : "error"}>{message.text}</span>
            : "AgroPrecio revisa solo cada sábado en la mañana si el DANE publicó un boletín nuevo."}
        </p>
      </div>
      <button className="btn" onClick={start} disabled={running}>
        {running ? <><span className="spinner" /> Actualizando…</> : "Buscar boletín nuevo"}
      </button>
    </section>
  );
}

// ---------- Lista de mercado ----------

function ShoppingList({ list, setList, byProduct, onPick }) {
  const [draft, setDraft] = useState({ restaurante: list.restaurante, items: list.items });
  const [saved, setSaved] = useState(true);
  const [adding, setAdding] = useState("");
  const timer = useRef(null);

  const save = (next) => {
    setDraft(next);
    setSaved(false);
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      const body = { restaurante: next.restaurante, items: next.items.map(({ producto, kg_semana }) => ({ producto, kg_semana: Number(kg_semana) || 0 })) };
      const fresh = await api("/lista", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setList(fresh);
      setSaved(true);
    }, 500);
  };

  const setKg = (producto, kg) =>
    save({ ...draft, items: draft.items.map((i) => (i.producto === producto ? { ...i, kg_semana: kg } : i)) });
  const remove = (producto) => save({ ...draft, items: draft.items.filter((i) => i.producto !== producto) });
  const add = () => {
    if (!adding) return;
    save({ ...draft, items: [...draft.items, { producto: adding, kg_semana: 1 }] });
    setAdding("");
  };

  const costs = Object.fromEntries(list.items.map((i) => [i.producto, i]));
  const missing = Object.keys(byProduct).filter((p) => !draft.items.some((i) => i.producto === p)).sort();

  return (
    <div className="card list">
      <div className="card-head">
        <div>
          <h2>Mi lista de mercado</h2>
          <input
            className="restaurant"
            value={draft.restaurante}
            onChange={(e) => save({ ...draft, restaurante: e.target.value })}
            aria-label="Nombre del restaurante"
          />
        </div>
        <span className="muted small">{saved ? "Guardada ✓" : "Guardando…"}</span>
      </div>

      {draft.items.length === 0 ? (
        <div className="empty">
          <p>Anota lo que compras cada semana en Cavasa y cuántos kilos. AgroPrecio te dice qué comprar ya, qué esperar y cuánto te va a costar.</p>
          <button className="btn" onClick={() => save({ ...draft, items: EXAMPLE_LIST })}>Usar una lista de ejemplo</button>
        </div>
      ) : (
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th>Producto</th><th>Kilos / semana</th><th>Hoy / kg</th><th>Próx. semana / kg</th>
                <th>Qué hacer</th><th title="Cuántas veces acertó el modelo con este producto en las últimas semanas">¿Le atina?</th>
                <th className="num">Costo hoy</th><th />
              </tr>
            </thead>
            <tbody>
              {draft.items.map((item) => {
                const a = byProduct[item.producto];
                const c = costs[item.producto];
                return (
                  <tr key={item.producto} onClick={() => onPick(item.producto)}>
                    <td><span className="icon" aria-hidden="true">{ICONS[item.producto]}</span>{item.producto}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <input type="number" min="0" step="0.5" className="kg" value={item.kg_semana}
                        onChange={(e) => setKg(item.producto, e.target.value)} aria-label={`Kilos de ${item.producto}`} />
                    </td>
                    <td className="num">{pesos(a.precio)}</td>
                    <td className="num range">{pesos(a.precio_min_esperado)} – {pesos(a.precio_max_esperado)}</td>
                    <td><span className={ACTION[a.prediccion].className}>{ACTION[a.prediccion].text}</span></td>
                    <td><Hits a={a} /></td>
                    <td className="num">{c ? pesos(c.costo_hoy) : "…"}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <button className="remove" onClick={() => remove(item.producto)} aria-label={`Quitar ${item.producto}`}>×</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {missing.length > 0 && (
        <div className="add">
          <select value={adding} onChange={(e) => setAdding(e.target.value)} aria-label="Producto para agregar">
            <option value="">Agregar un producto…</option>
            {missing.map((p) => <option key={p} value={p}>{ICONS[p]} {p}</option>)}
          </select>
          <button className="btn small-btn" onClick={add} disabled={!adding}>Agregar</button>
        </div>
      )}
    </div>
  );
}

function Hits({ a }) {
  if (!a.evaluadas) return <span className="muted small">sin datos</span>;
  return (
    <span className="hits" title={`Acertó ${a.aciertos} de las últimas ${a.evaluadas} semanas`}>
      {Array.from({ length: a.evaluadas }, (_, i) => <i key={i} className={i < a.aciertos ? "on" : ""} />)}
      <span className="small">{a.aciertos}/{a.evaluadas}</span>
    </span>
  );
}

function Totals({ totals, hasItems }) {
  if (!hasItems) return null;
  const vsToday = totals.costo_hoy - totals.costo_recomendado;
  const vsNext = totals.costo_proxima - totals.costo_recomendado;
  return (
    <div className="card totals">
      <div className="cover" role="img" aria-label="Puesto de verduras en una plaza de mercado" />
      <h2>Tu mercado de la semana</h2>
      <div className="total main">
        <span>Siguiendo AgroPrecio</span>
        <strong>{pesos(totals.costo_recomendado)}</strong>
      </div>
      <div className="total"><span>Si compras todo hoy</span><span>{pesos(totals.costo_hoy)}</span></div>
      <div className="total"><span>Si esperas todo a la próxima semana</span><span>≈ {pesos(totals.costo_proxima)}</span></div>
      <p className="small saving">
        {vsNext > 0 && <>Te ahorras cerca de <strong>{pesos(vsNext)}</strong> frente a esperar todo. </>}
        {vsToday > 0 && <>Y <strong>{pesos(vsToday)}</strong> frente a comprar todo hoy.</>}
        {vsNext <= 0 && vsToday <= 0 && "Esta semana no hay mucha diferencia: compra como de costumbre."}
      </p>
      <p className="muted small">Lo que sube se compra hoy, lo que baja se deja para la próxima semana y lo estable como siempre.</p>
    </div>
  );
}

function Bulletin({ bulletin }) {
  const [copied, setCopied] = useState(false);
  if (!bulletin?.texto) return null;
  const copy = async () => {
    await navigator.clipboard.writeText(bulletin.texto);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="card note">
      <div className="card-head">
        <h2>El boletín de la semana</h2>
        <button className="link" onClick={copy}>{copied ? "Copiado ✓" : "Copiar"}</button>
      </div>
      <p className="bulletin">{bulletin.texto}</p>
      <p className="muted small">Redactado con {bulletin.fuente === "claude" ? "Claude" : "la plantilla de AgroPrecio"}.</p>
    </div>
  );
}

// ---------- Pizarra con los 20 productos ----------

function Board({ alerts, week, selected, onPick }) {
  return (
    <section className="board" aria-label="Pizarra de precios">
      <h2>Pizarra de Cavasa · semana del {day(week)}</h2>
      <div className="board-grid">
        {alerts.map((a) => (
          <button key={a.producto} className={"slot" + (a.producto === selected ? " selected" : "")} onClick={() => onPick(a.producto)}>
            <span className="slot-name"><span aria-hidden="true">{ICONS[a.producto]}</span> {a.producto}</span>
            <span className="price">{pesos(a.precio)}<small>/kg</small></span>
            <span className={"change " + (a.cambio_1s > 0 ? "up" : "down")}>
              {a.cambio_1s > 0 ? "▲" : "▼"} {pct(a.cambio_1s)} vs. semana pasada
            </span>
            <span className={ACTION[a.prediccion].className}>Próx.: {ACTION[a.prediccion].hint}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

// ---------- Detalle de un producto ----------

function ProductDetail({ alert: a }) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api(`/historico/${encodeURIComponent(a.producto)}?semanas=26`).then(setHistory).catch(() => setHistory([]));
  }, [a.producto]);

  if (!history.length) return null;

  const next = addDays(a.semana_inicio, 7);
  const data = history.map((r) => ({ semana: r.semana_inicio.slice(0, 10), precio: r.precio, nacional: r.precio_nacional }));
  data[data.length - 1].rango = [a.precio, a.precio];
  data.push({ semana: next, rango: [a.precio_min_esperado, a.precio_max_esperado] });

  return (
    <section className="card detail">
      <h2><span aria-hidden="true">{ICONS[a.producto]}</span> {a.producto}: últimos 6 meses y lo que viene</h2>
      <p className="detail-text">
        Hoy está en <strong>{pesos(a.precio)}/kg</strong> en Cavasa
        ({a.cambio_1s > 0 ? "subió" : "bajó"} {pct(a.cambio_1s)} frente a la semana pasada).
        Para la semana del {day(next)} se espera que <strong>{ACTION[a.prediccion].hint.replace("se espera que ", "")}</strong>:
        entre <strong>{pesos(a.precio_min_esperado)}</strong> y <strong>{pesos(a.precio_max_esperado)}</strong> por kilo.
        {a.evaluadas ? ` Con este producto el modelo acertó ${a.aciertos} de las últimas ${a.evaluadas} semanas.` : ""}
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={data} margin={{ left: 4, right: 12, top: 8 }}>
          <CartesianGrid stroke="var(--line)" vertical={false} />
          <XAxis dataKey="semana" tickFormatter={(d) => day(d)} tick={{ fontSize: 11, fill: "var(--muted)" }} minTickGap={36} />
          <YAxis tickFormatter={(v) => "$" + (v / 1000).toLocaleString("es-CO") + " mil"} tick={{ fontSize: 11, fill: "var(--muted)" }} width={64} domain={["auto", "auto"]} />
          <Tooltip
            labelFormatter={(d) => "Semana del " + day(d)}
            formatter={(v, name) => [Array.isArray(v) ? `${pesos(v[0])} – ${pesos(v[1])}` : pesos(v), name]}
            contentStyle={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: 8 }}
          />
          <Area dataKey="rango" name="Rango esperado" stroke="none" fill="var(--maiz)" fillOpacity={0.45} />
          <Line dataKey="nacional" name="Mediana nacional" stroke="var(--muted)" strokeDasharray="4 4" dot={false} />
          <Line dataKey="precio" name="Cavasa" stroke="var(--tomate)" strokeWidth={2.5} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="legend small muted">
        <span className="key tomate" /> Cavasa <span className="key dashed" /> Mediana nacional <span className="key maiz" /> Rango esperado para la próxima semana
      </p>
    </section>
  );
}
