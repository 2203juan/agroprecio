import { useEffect, useRef, useState } from "react";
import {
  Area, Bar, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const API = "/api";

// Qué hacer según la predicción. El color es solo de la acción:
// el cambio de la semana pasada va en gris para no confundirlos
const ACTION = {
  sube: { text: "Compra ya", icon: "🛒", why: "se espera que suba", className: "chip ya" },
  baja: { text: "Espera", icon: "⏳", why: "se espera que baje", className: "chip espera" },
  estable: { text: "Como siempre", icon: "👌", why: "sin cambio importante o sin señal clara", className: "chip normal" },
};
const ORDER = ["sube", "baja", "estable"];

// Foto de cada producto (créditos en public/img/productos/CREDITOS.md)
const PHOTOS = {
  "Aguacate papelillo": "aguacate", "Ahuyama": "ahuyama", "Cebolla cabezona blanca bogotana": "cebolla-cabezona",
  "Cebolla junca Aquitania": "cebolla-junca", "Cilantro": "cilantro", "Habichuela": "habichuela", "Lechuga Batavia": "lechuga",
  "Limón Tahití": "limon", "Lulo": "lulo", "Mango Tommy": "mango", "Maracuyá": "maracuya", "Mora de Castilla": "mora",
  "Papa capira": "papa-capira", "Papa parda pastusa": "papa-pastusa", "Pimentón": "pimenton", "Plátano hartón verde": "platano",
  "Tomate chonto": "tomate-chonto", "Tomate de árbol": "tomate-arbol", "Yuca ICA": "yuca", "Zanahoria bogotana": "zanahoria",
};

// Decorativa: el nombre del producto siempre va al lado
function Photo({ name, className = "photo" }) {
  const file = PHOTOS[name];
  if (!file) return <span className={className + " empty-photo"} aria-hidden="true" />;
  return <img className={className} src={`/img/productos/${file}.webp`} alt="" loading="lazy" width="400" height="400" />;
}

// Gramos de cada producto por plato (sopa, seco, ensalada, tajadas y jugo); de ahí salen los kilos de la semana
// Mercados de ejemplo: gramos por plato, para 500 platos diarios de lunes a sábado
const EXAMPLE = { diners: 500, days: 6 };
const asList = (grams) => Object.entries(grams).map(([producto, g]) => (
  { producto, kg_semana: Math.max(1, Math.round((g * EXAMPLE.diners * EXAMPLE.days) / 1000)) }
));
const EXAMPLES = [
  {
    name: "Restaurante de almuerzos", label: `${EXAMPLE.diners} almuerzos diarios, de lunes a sábado`,
    items: asList({
      "Papa parda pastusa": 100, "Plátano hartón verde": 100, "Tomate chonto": 60, "Papa capira": 50, "Yuca ICA": 50,
      "Cebolla cabezona blanca bogotana": 40, "Zanahoria bogotana": 40, "Ahuyama": 40, "Habichuela": 30, "Limón Tahití": 30,
      "Lechuga Batavia": 25, "Aguacate papelillo": 25, "Cebolla junca Aquitania": 20, "Pimentón": 15, "Cilantro": 10,
      "Lulo": 20, "Mora de Castilla": 20, "Maracuyá": 20, "Mango Tommy": 20, "Tomate de árbol": 20,
    }),
  },
  {
    // Casi todo el gasto se va en limón y cebolla, dos productos que cambian mucho de una semana a otra
    name: "Cevichería", label: `${EXAMPLE.diners} ceviches diarios, de lunes a sábado`,
    items: asList({
      "Limón Tahití": 150, "Plátano hartón verde": 120, "Cebolla cabezona blanca bogotana": 80, "Lechuga Batavia": 40,
      "Tomate chonto": 40, "Lulo": 40, "Aguacate papelillo": 30, "Maracuyá": 30, "Pimentón": 15, "Cilantro": 15,
    }),
  },
];
const kilos = (items) => items.reduce((t, i) => t + i.kg_semana, 0).toLocaleString("es-CO");

const pesos = (n) => "$" + Math.round(n).toLocaleString("es-CO");
const pct = (n) => Math.round(Math.abs(n) * 100) + " %";
const day = (d, opts = { day: "numeric", month: "short" }) =>
  new Date(d.slice(0, 10) + "T12:00:00").toLocaleDateString("es-CO", opts);
// "7 al 13 de nov": no repite el mes cuando es el mismo
const span = (a, b, opts) => `${a.slice(0, 7) === b.slice(0, 7) ? Number(a.slice(8, 10)) : day(a)} al ${day(b, opts)}`;
const addDays = (d, n) => {
  const x = new Date(d.slice(0, 10) + "T12:00:00");
  x.setDate(x.getDate() + n);
  return x.toISOString().slice(0, 10);
};

// Sin tildes ni mayúsculas, para buscar "limon" y encontrar "Limón"
const plain = (text) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const whatsapp = (text) => "https://wa.me/?text=" + encodeURIComponent(text);

function WhatsApp({ text, children }) {
  return <a className="btn wa" href={whatsapp(text)} target="_blank" rel="noopener noreferrer">{children}</a>;
}

// En la versión pública la lista de mercado se guarda en el navegador de cada persona
const LIST_KEY = "agroprecio.lista";
const local = {
  on: false,
  read() { try { return JSON.parse(localStorage.getItem(LIST_KEY)); } catch { return null; } },
  write(body) { try { localStorage.setItem(LIST_KEY, JSON.stringify(body)); } catch { /* sin almacenamiento: la lista dura lo que dure la pestaña */ } },
};
// Lo que se muestra es la recomendación: la clase del modelo solo cuando tuvo confianza
// suficiente. Con poca confianza el producto queda "sin señal clara" y se compra como siempre
const asShown = (a) => ({ ...a, modelo: a.prediccion, prediccion: a.recomendacion ?? a.prediccion, weak: a.senal === "debil" });
const shownList = (l) => ({ ...l, items: l.items.map(asShown) });
const putList = (body) => api("/lista", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(shownList);

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
  const [validity, setValidity] = useState(null);
  const [error, setError] = useState(null);

  const load = () =>
    Promise.all([api("/alertas"), api("/boletin"), api("/modelo"), api("/lista"), api("/vigencia")])
      .then(async ([a, b, m, l, v]) => {
        local.on = !!v.publico;
        const mine = local.on && local.read();
        l = mine?.items?.length ? await putList(mine) : shownList(l);
        a = a.map(asShown);
        setAlerts(a);
        setBulletin(b);
        setModel(m.produccion);
        setList(l);
        setValidity(v);
        return a;
      })
      .catch((e) => setError(e.message));

  useEffect(() => { load(); }, []);

  if (error) return <Shell><p className="error">No se pudo conectar con la API ({error}).</p></Shell>;
  if (!alerts.length || !list) return <Shell><p className="muted">Cargando precios…</p></Shell>;

  const week = alerts[0].semana_inicio;
  const byProduct = Object.fromEntries(alerts.map((a) => [a.producto, a]));
  // Semana para la que vale la recomendación
  const target = {
    start: validity?.recomendacion_inicio ?? addDays(week, 7),
    end: validity?.recomendacion_fin ?? addDays(week, 13),
    expired: !!validity?.vencida,
  };

  return (
    <Shell>
      <Status week={week} validity={validity} onDone={load} />
      <Hero alerts={alerts} list={list} target={target} onPick={setProduct} />

      <section className="layout">
        <ShoppingList list={list} setList={setList} byProduct={byProduct} week={week} onPick={setProduct} />
        <aside className="side">
          <Totals list={list} week={week} target={target} />
          <Feedback week={week} restaurant={list.restaurante} />
          <Bulletin bulletin={bulletin} alerts={alerts} onPick={setProduct} />
        </aside>
      </section>

      <RealSavings saving={list.ahorro_real} />

      <Board alerts={alerts} week={week} onPick={setProduct} />

      <footer>
        <p className="brand">Agro<span>Precio</span></p>
        <p>
          Precios mayoristas de Cavasa, la central de abastos que surte a Cali (queda en Candelaria, Valle del Cauca), publicados por el SIPSA – DANE, en pesos por kilo.
          Las proyecciones son estimaciones{model ? ` del modelo ${model.version}` : ""}: el precio real puede cambiar.
        </p>
        {model?.metricas?.modelo?.accuracy_senal_clara != null && (
          <p>
            Solo decimos "compra ya" o "espera" cuando el modelo tiene una señal clara. En las últimas {" "}
            {model.metricas.modelo.n / alerts.length} semanas de prueba eso pasó en {Math.round(model.metricas.modelo.cobertura_senal_clara * 100)} % de los casos,
            y acertó {Math.round(model.metricas.modelo.accuracy_senal_clara * 100)} % de las veces.
          </p>
        )}
      </footer>

      <DetailDialog alert={product ? byProduct[product] : null} onClose={() => setProduct(null)} />
    </Shell>
  );
}

function Shell({ children }) {
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <p className="brand">
            <svg viewBox="0 0 32 32" aria-hidden="true"><path d="M27 4C13 4 5 11 5 20c0 2 .5 3.800 1.300 5.300C10 17 16 12 23 9.500 16.500 13.500 11.500 19 9 27.500c1.300.3 2.700.5 4 .5 9 0 15-8 14-24Z" /></svg>
            Agro<span>Precio</span>
          </p>
          <p className="topbar-note">Precios de la plaza para tu cocina · Cali</p>
        </div>
      </header>
      <main className="page">{children}</main>
    </>
  );
}

// ---------- De cuándo son los precios, y si la recomendación sigue vigente ----------

function Status({ week, validity, onDone }) {
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
        : { ok: true, text: "El DANE todavía no ha publicado un boletín nuevo." });
    }, 2000);
  };

  useEffect(() => {
    // Si ya había una actualización corriendo (por ejemplo la automática), la seguimos
    if (!validity?.publico) api("/actualizar").then((s) => { setJob(s); if (s.corriendo) poll(week); }).catch(() => {});
    return () => clearTimeout(timer.current);
  }, []);

  const start = async () => {
    setMessage(null);
    setJob(await api("/actualizar", { method: "POST" }));
    poll(week);
  };

  const running = job?.corriendo;
  const lastLine = job?.ultimas_lineas?.at(-1)?.replace(/^\S+ \S+ \w+ /, "");
  const expired = validity?.vencida;

  return (
    <section className={"status" + (expired ? " expired" : "")} role="status">
      <div className="status-text">
        <p className="week">
          Precios del <strong>{span(week.slice(0, 10), addDays(week, 6), { day: "numeric", month: "short", year: "numeric" })}</strong>
          <span className="muted"> · último boletín del DANE</span>
        </p>
        {expired ? (
          <p>
            <strong>Recomendación vencida.</strong> Era para la semana del {span(validity.recomendacion_inicio, validity.recomendacion_fin)}.
            <span className="long"> Úsala solo como referencia hasta que salga el boletín siguiente.</span>
          </p>
        ) : (
          <p className="muted small">AgroPrecio busca el boletín nuevo cada {validity?.publico ? "miércoles y sábado" : "sábado en la mañana"}.</p>
        )}
        {running && <p className="muted small"><span className="spinner dark" /> Buscando en el DANE… {lastLine ?? ""}</p>}
        {!running && message && <p className={"small " + (message.ok ? "ok" : "error")}>{message.text}</p>}
      </div>
      {!validity?.publico && (
        <button className="link refresh" onClick={start} disabled={running}>
          {running ? "Buscando…" : "Buscar boletín nuevo"}
        </button>
      )}
    </section>
  );
}

// ---------- La respuesta, arriba: qué comprar ya y qué esperar ----------

function Hero({ alerts, list, target, onPick }) {
  const mine = list.items.length > 0;
  const source = mine ? list.items : alerts;
  return (
    <section className="hero" aria-label="Resumen de la semana">
      <div className="hero-panel">
        <div className="hero-copy">
          <p className="kicker">Cavasa · central de abastos de Cali</p>
          <h1>Qué comprar <span className="outline">esta semana</span></h1>
          <p className="hero-sub">
            {mine ? "Tu lista" : `Los ${alerts.length} productos`} para la semana del {span(target.start, target.end)}{target.expired ? " (ya pasó)" : ""}
          </p>
        </div>
        {mine && (
          <div className="tab">
            <span>Tu mercado</span>
            <strong>{pesos(list.totales.costo_recomendado)}</strong>
            <span>siguiendo la recomendación</span>
          </div>
        )}
      </div>
      <div className="summary-grid">
        {ORDER.map((k) => {
          const items = source.filter((a) => a.prediccion === k);
          return (
            <div key={k} className={"sum " + k}>
              <span className="sum-count">{items.length}</span>
              <div className="sum-head">
                <p className="sum-title">{ACTION[k].text}</p>
                <p className="sum-why">{ACTION[k].why}</p>
              </div>
              <p className="sum-names">
                {items.length === 0 ? <span className="muted">Ninguno esta semana</span> : items.map((a, i) => (
                  <span key={a.producto}>
                    <button className="name-link" onClick={() => onPick(a.producto)}>{a.producto}</button>
                    {i < items.length - 1 ? ", " : ""}
                  </span>
                ))}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ---------- Lista de mercado ----------

function ShoppingList({ list, setList, byProduct, week, onPick }) {
  const [draft, setDraft] = useState({ restaurante: list.restaurante, items: list.items });
  const [saved, setSaved] = useState(true);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [removed, setRemoved] = useState(null);
  const timer = useRef(null);
  const undoTimer = useRef(null);

  const save = (next) => {
    setDraft(next);
    setSaved(false);
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      const body = { restaurante: next.restaurante, items: next.items.map(({ producto, kg_semana }) => ({ producto, kg_semana: Number(kg_semana) || 0 })) };
      const fresh = await putList(body);
      if (local.on) local.write(body);
      setList(fresh);
      setSaved(true);
    }, 500);
  };

  const setKg = (producto, kg) =>
    save({ ...draft, items: draft.items.map((i) => (i.producto === producto ? { ...i, kg_semana: kg } : i)) });

  const remove = (producto) => {
    const index = draft.items.findIndex((i) => i.producto === producto);
    setRemoved({ item: draft.items[index], index });
    clearTimeout(undoTimer.current);
    undoTimer.current = setTimeout(() => setRemoved(null), 7000);
    save({ ...draft, items: draft.items.filter((i) => i.producto !== producto) });
  };
  const undo = () => {
    if (!removed || draft.items.some((i) => i.producto === removed.item.producto)) return setRemoved(null);
    const items = [...draft.items];
    items.splice(removed.index, 0, removed.item);
    save({ ...draft, items });
    setRemoved(null);
  };
  const add = (producto) => {
    save({ ...draft, items: [...draft.items, { producto, kg_semana: 1 }] });
    setQuery("");
  };

  useEffect(() => () => clearTimeout(undoTimer.current), []);

  const costs = Object.fromEntries(list.items.map((i) => [i.producto, i]));
  const missing = Object.keys(byProduct).filter((p) => !draft.items.some((i) => i.producto === p)).sort();
  const lastDay = day(addDays(week, 6));
  const matches = missing.filter((p) => plain(p).includes(plain(query.trim())));

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
          <div className="examples">
            {EXAMPLES.map((e) => (
              <button key={e.name} className="btn" onClick={() => save({ ...draft, items: e.items })}>Probar con: {e.name.toLowerCase()}</button>
            ))}
          </div>
          <p className="muted small">Son mercados de ejemplo: {EXAMPLES.map((e) => `${e.label} (${kilos(e.items)} kilos a la semana)`).join("; ")}.</p>
        </div>
      ) : (
        <ul className="items">
          {draft.items.map((item) => {
            const a = byProduct[item.producto];
            const c = costs[item.producto];
            const action = ACTION[a.prediccion];
            return (
              <li key={item.producto} className="item">
                <button className="item-name" onClick={() => onPick(item.producto)} title="Ver cómo ha cambiado el precio">
                  <Photo name={item.producto} className="thumb" />
                  <span>{item.producto}</span>
                  <span className="more" aria-hidden="true">›</span>
                </button>
                <span className={"item-action " + action.className} title={a.weak ? "El modelo no tiene una señal clara para este producto" : undefined}>
                  {a.weak ? "Sin señal clara" : action.text}
                </span>
                <dl className="item-prices">
                  <div><dt>Último ({lastDay})</dt><dd>{pesos(a.precio)}/kg</dd></div>
                  <div><dt>Próxima semana</dt><dd>{pesos(a.precio_min_esperado)} – {pesos(a.precio_max_esperado)}</dd></div>
                  <div className="hit" title="Semanas en que la recomendación de este producto resultó correcta">
                    <dt>Ha acertado</dt><dd>{a.evaluadas ? `${a.aciertos} de ${a.evaluadas} veces` : "sin historial"}</dd>
                  </div>
                </dl>
                <Stepper value={item.kg_semana} label={item.producto} onChange={(kg) => setKg(item.producto, kg)} />
                <div className="item-cost">
                  <span className="label">Costo</span>
                  <strong>{c ? pesos(c.costo_hoy) : "…"}</strong>
                </div>
                <button className="remove" onClick={() => remove(item.producto)} aria-label={`Quitar ${item.producto}`}>×</button>
              </li>
            );
          })}
        </ul>
      )}

      {missing.length > 0 && (
        <div className="add">
          <input type="search" value={query} placeholder="Buscar un producto para agregar…" aria-label="Buscar un producto para agregar"
            onChange={(e) => setQuery(e.target.value)} onFocus={() => setSearching(true)} onBlur={() => setSearching(false)}
            onKeyDown={(e) => { if (e.key === "Enter" && matches.length) add(matches[0]); if (e.key === "Escape") e.target.blur(); }} />
          {(searching || query) && (
            <ul className="suggest" aria-label="Productos para agregar">
              {matches.length === 0 && <li className="muted none">No hay un producto con ese nombre en Cavasa.</li>}
              {matches.map((p) => (
                <li key={p}>
                  {/* onMouseDown evita que el buscador pierda el foco antes del clic */}
                  <button onMouseDown={(e) => e.preventDefault()} onClick={() => add(p)}>
                    <Photo name={p} className="thumb small" /> {p} <span className="plus" aria-hidden="true">+ Agregar</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {draft.items.length > 0 && (
        <p className="small muted examples-inline">
          Cambiar por un mercado de ejemplo:{" "}
          {EXAMPLES.map((e) => (
            <button key={e.name} className="link small" onClick={() => save({ ...draft, items: e.items })} title={e.label}>{e.name}</button>
          ))}
        </p>
      )}

      {removed && (
        <div className="toast" role="status">
          <span>Quitaste {removed.item.producto}</span>
          <button onClick={undo}>Deshacer</button>
        </div>
      )}
    </div>
  );
}

function Stepper({ value, label, onChange }) {
  const n = Number(value) || 0;
  const clean = (text) => text.replace(",", ".").replace(/[^\d.]/g, "");
  return (
    <div className="stepper">
      <button onClick={() => onChange(Math.max(0, n - 1))} disabled={n <= 0} aria-label={`Un kilo menos de ${label}`}>−</button>
      <label>
        <input type="text" inputMode="decimal" value={value} onChange={(e) => onChange(clean(e.target.value))}
          onFocus={(e) => e.target.select()} aria-label={`Kilos de ${label} por semana`} />
        <span aria-hidden="true">kg</span>
      </label>
      <button onClick={() => onChange(n + 1)} aria-label={`Un kilo más de ${label}`}>+</button>
    </div>
  );
}

function Totals({ list, week, target }) {
  const totals = list.totales;
  if (!list.items.length) return null;
  const vsToday = totals.costo_hoy - totals.costo_recomendado;
  const vsNext = totals.costo_proxima - totals.costo_recomendado;
  const lines = ORDER.map((k) => {
    const items = list.items.filter((i) => i.prediccion === k);
    return items.length ? `${ACTION[k].icon} *${ACTION[k].text}:* ${items.map((i) => `${i.producto} (${i.kg_semana} kg)`).join(", ")}` : null;
  }).filter(Boolean);
  const message = [
    `*Mercado de ${list.restaurante}* · precios de Cavasa al ${day(addDays(week, 6))}`,
    ...lines,
    `Total siguiendo la recomendación: ${pesos(totals.costo_recomendado)}`,
    target.expired ? `Ojo: la recomendación era para la semana del ${span(target.start, target.end)}.` : `Recomendación para la semana del ${span(target.start, target.end)}.`,
    "Son estimaciones de AgroPrecio con datos del SIPSA - DANE.",
  ].join("\n");
  return (
    <div className="card totals">
            <h2>Tu mercado de la semana</h2>
      <div className="total main">
        <span>Siguiendo la recomendación</span>
        <strong>{pesos(totals.costo_recomendado)}</strong>
      </div>
      <div className="total"><span>Si compras todo ya</span><span>{pesos(totals.costo_hoy)}</span></div>
      <div className="total"><span>Si esperas todo una semana</span><span>≈ {pesos(totals.costo_proxima)}</span></div>
      <p className="small saving">
        {vsNext > 0 && <>Si las predicciones se cumplen, te ahorras cerca de <strong>{pesos(vsNext)}</strong> frente a esperar todo. </>}
        {vsToday > 0 && <>Y <strong>{pesos(vsToday)}</strong> frente a comprar todo ya.</>}
        {vsNext <= 0 && vsToday <= 0 && "Esta semana no hay mucha diferencia: compra como de costumbre."}
      </p>
      <p className="muted small">Lo que va a subir se compra ya, lo que va a bajar se deja para la otra semana y el resto como siempre.</p>
      <WhatsApp text={message}>Enviar mi lista por WhatsApp</WhatsApp>
    </div>
  );
}

// ---------- Ahorro real de la lista con precios que ya pasaron ----------

function RealSavings({ saving }) {
  const r = saving?.resumen;
  if (!r) return null;
  const won = r.ahorro >= 0;
  const data = saving.semanas.map((w) => ({ semana: String(w.semana_inicio).slice(0, 10), ahorro: w.ahorro, acumulado: w.ahorro_acumulado }));
  const thousands = (v) => (v < 0 ? "-$" : "$") + Math.abs(Math.round(v / 1000)).toLocaleString("es-CO") + " mil";
  const signed = (v) => (v < 0 ? "-" : "") + pesos(Math.abs(v));
  return (
    <section className="card savings" aria-label="Ahorro real con tu lista">
      <div className="savings-head">
        <p className="kicker">Con precios reales, no con estimaciones</p>
        <h2>Lo que habrías {won ? "ahorrado" : "perdido"} con esta lista</h2>
        <p className="muted">
          Tomamos las últimas {r.semanas} semanas ({day(r.desde)} a {day(addDays(r.hasta, 6), { day: "numeric", month: "short", year: "numeric" })}),
          con la recomendación que dio AgroPrecio cada semana y el precio que después publicó el DANE.
        </p>
      </div>

      <div className="stats">
        <div className={"stat big " + (won ? "good" : "bad")}>
          <span className="label">{won ? "Ahorro" : "Pérdida"} en {r.semanas} semanas</span>
          <strong>{signed(r.ahorro)}</strong>
          <span className="muted small">{(Math.abs(r.ahorro_pct) * 100).toFixed(1).replace(".", ",")} % del mercado</span>
        </div>
        <div className="stat">
          <span className="label">Por semana, en promedio</span>
          <strong>{signed(r.ahorro_por_semana)}</strong>
        </div>
        <div className="stat">
          <span className="label">En un año, a este ritmo</span>
          <strong>{signed(r.ahorro_al_anio)}</strong>
        </div>
        <div className="stat">
          <span className="label">Semanas en que salió mejor</span>
          <strong>{r.semanas_con_ahorro} de {r.semanas}</strong>
          <span className="muted small">{r.semanas_con_perdida} salieron más caras</span>
        </div>
      </div>

      {r.esperas > 0 && (
        <div className="stats waits">
          <div className="stat good">
            <span className="label">En lo que te dijo "espera"</span>
            <strong>{(r.ahorro_en_esperas_pct * 100).toFixed(1).replace(".", ",")} % menos</strong>
            <span className="muted small">pagaste por esas compras</span>
          </div>
          <div className="stat">
            <span className="label">Veces que esperar salió bien</span>
            <strong>{r.esperas_acertadas} de {r.esperas}</strong>
            <span className="muted small">el resto de la lista se compró como siempre</span>
          </div>
          <div className="stat">
            <span className="label">La mejor semana ({day(r.mejor_semana.semana_inicio)})</span>
            <strong>{signed(r.mejor_semana.ahorro)}</strong>
            <span className="muted small">{(r.mejor_semana.ahorro_pct * 100).toFixed(1).replace(".", ",")} % del mercado de esa semana</span>
          </div>
        </div>
      )}

      <div className="compare">
        <div><span>Comprando todo ya, como siempre</span><span>{pesos(r.costo_habitual)}</span></div>
        <div className="main"><span>Siguiendo la recomendación</span><span>{pesos(r.costo_recomendado)}</span></div>
      </div>

      <h3>Ahorro de cada semana y cómo se va sumando</h3>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={data} margin={{ left: 4, right: 12, top: 8 }}>
          <CartesianGrid stroke="var(--line)" vertical={false} />
          <XAxis dataKey="semana" tickFormatter={(d) => day(d)} tick={{ fontSize: 12, fill: "var(--muted)" }} minTickGap={28} />
          <YAxis tickFormatter={thousands} tick={{ fontSize: 12, fill: "var(--muted)" }} width={72} />
          <Tooltip
            labelFormatter={(d) => "Semana del " + day(d)}
            formatter={(v, name) => [signed(v), name]}
            contentStyle={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: 8 }}
          />
          <ReferenceLine y={0} stroke="var(--muted)" />
          <Bar dataKey="ahorro" name="Ahorro de la semana" radius={[4, 4, 0, 0]}>
            {data.map((d) => <Cell key={d.semana} fill={d.ahorro >= 0 ? "var(--green)" : "var(--red)"} />)}
          </Bar>
          <Line dataKey="acumulado" name="Ahorro acumulado" stroke="var(--forest)" strokeWidth={2.5} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="legend small muted">
        <span className="key bar good" /> Semana con ahorro <span className="key bar bad" /> Semana que salió más cara <span className="key line" /> Ahorro acumulado
      </p>

      <p className="small muted savings-note">
        Cómo se calcula: cada semana se compra la misma lista. "Como siempre" es comprar todo ya; siguiendo la recomendación,
        lo que AgroPrecio dijo que iba a bajar se compró a la semana siguiente, al precio real de esa semana. No siempre acierta.
        Sabiendo el futuro, el ahorro máximo posible era {pesos(r.ahorro_maximo_posible)}
        {r.ahorro > 0 ? <>: la recomendación logró el {Math.round(r.parte_del_maximo * 100)} % de eso.</> : "."}
      </p>
    </section>
  );
}

function Bulletin({ bulletin, alerts, onPick }) {
  const [copied, setCopied] = useState(false);
  if (!bulletin?.texto) return null;
  const copy = async () => {
    await navigator.clipboard.writeText(bulletin.texto);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="card note">
      <h2>El boletín de la semana</h2>
      <p className="muted small">Los {alerts.length} productos que seguimos en Cavasa.</p>
      {ORDER.map((k) => {
        const items = alerts.filter((a) => a.prediccion === k);
        if (!items.length) return null;
        return (
          <div key={k} className="group">
            <h3>{ACTION[k].text} <span className="muted">· {ACTION[k].why}</span></h3>
            <p>
              {items.map((a, i) => (
                <span key={a.producto}>
                  <button className="name-link" onClick={() => onPick(a.producto)}>{a.producto}</button>{i < items.length - 1 ? ", " : ""}
                </span>
              ))}
            </p>
          </div>
        );
      })}
      <details>
        <summary>Leer el texto para enviar</summary>
        <p className="bulletin">{bulletin.texto}</p>
        <p className="muted small">Redactado con {bulletin.fuente === "claude" ? "Claude" : "la plantilla de AgroPrecio"}.</p>
      </details>
      <div className="share">
        <WhatsApp text={bulletin.texto}>Enviar por WhatsApp</WhatsApp>
        <button className="link" onClick={copy}>{copied ? "Copiado ✓" : "Copiar texto"}</button>
      </div>
    </div>
  );
}

// ---------- ¿Te sirvió? ----------

function Feedback({ week, restaurant }) {
  const key = `opinion-${week}`;
  const [sent, setSent] = useState(() => { try { return !!localStorage.getItem(key); } catch { return false; } });
  const [comment, setComment] = useState("");
  const [error, setError] = useState(null);

  const send = async (util) => {
    setError(null);
    try {
      await api("/opiniones", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ util, restaurante: restaurant, comentario: comment }),
      });
      setSent(true);
      try { localStorage.setItem(key, "1"); } catch { /* sin almacenamiento: solo se puede repetir */ }
    } catch {
      setError("No se pudo guardar tu respuesta. Intenta otra vez.");
    }
  };

  return (
    <div className="card feedback">
      <h2>¿Te sirvió esta semana?</h2>
      {sent ? <p className="ok">¡Gracias! Tu respuesta quedó guardada.</p> : (
        <>
          <input value={comment} maxLength={300} onChange={(e) => setComment(e.target.value)}
            placeholder="¿Qué compraste distinto? (opcional)" aria-label="Comentario opcional" />
          <div className="feedback-buttons">
            <button className="btn" onClick={() => send(true)}>👍 Sí</button>
            <button className="btn plain" onClick={() => send(false)}>👎 No</button>
          </div>
          <p className="muted small">Se guarda con el nombre de tu restaurante. No escribas datos personales.</p>
          {error && <p className="error small">{error}</p>}
        </>
      )}
    </div>
  );
}

// ---------- Todos los precios, como un volante de ofertas ----------

function Board({ alerts, week, onPick }) {
  const [filter, setFilter] = useState(null);
  const [all, setAll] = useState(false);
  const shown = filter ? alerts.filter((a) => a.prediccion === filter) : alerts;
  const count = (k) => alerts.filter((a) => a.prediccion === k).length;
  return (
    <section className="board" aria-label="Todos los precios de Cavasa">
      <div className="board-head">
        <div>
          <p className="kicker">Precios al {day(addDays(week, 6))}</p>
          <h2>Todos los precios de Cavasa</h2>
        </div>
        <div className="filters" role="group" aria-label="Filtrar por recomendación">
          <button className="filter" aria-pressed={filter === null} onClick={() => setFilter(null)}>Todos ({alerts.length})</button>
          {ORDER.map((k) => (
            <button key={k} className="filter" aria-pressed={filter === k} onClick={() => setFilter(filter === k ? null : k)}>
              {ACTION[k].text} ({count(k)})
            </button>
          ))}
        </div>
      </div>
      <div className={"board-grid" + (all || filter ? " all" : "")}>
        {shown.map((a) => (
          <button key={a.producto} className="product" onClick={() => onPick(a.producto)}>
            <span className={"tag " + ACTION[a.prediccion].className}>{a.weak ? "Sin señal clara" : ACTION[a.prediccion].text}</span>
            <Photo name={a.producto} />
            <span className="product-name">{a.producto}</span>
            <span className="price">{pesos(a.precio)}<small>/kg</small></span>
            <span className="change">{a.cambio_1s > 0 ? "▲ Subió" : "▼ Bajó"} {pct(a.cambio_1s)} en la semana</span>
          </button>
        ))}
      </div>
      {!all && !filter && (
        <button className="filter show-all" onClick={() => setAll(true)}>Ver los {alerts.length} productos</button>
      )}
    </section>
  );
}

// ---------- Detalle de un producto, en un panel sobre la página ----------

function DetailDialog({ alert, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    const dialog = ref.current;
    if (alert && !dialog.open) dialog.showModal();
    if (!alert && dialog.open) dialog.close();
  }, [alert]);

  return (
    <dialog ref={ref} className="sheet" onClose={onClose} aria-labelledby="detail-title"
      onClick={(e) => { if (e.target === ref.current) onClose(); }}>
      {alert && <ProductDetail key={alert.producto} alert={alert} onClose={onClose} />}
    </dialog>
  );
}

function ProductDetail({ alert: a, onClose }) {
  const [history, setHistory] = useState(null);

  useEffect(() => {
    api(`/historico/${encodeURIComponent(a.producto)}?semanas=26`).then(setHistory).catch(() => setHistory([]));
  }, [a.producto]);

  const next = addDays(a.semana_inicio, 7);
  const action = ACTION[a.prediccion];
  let data = [];
  if (history?.length) {
    data = history.map((r) => ({ semana: r.semana_inicio.slice(0, 10), precio: r.precio, nacional: r.precio_nacional }));
    data[data.length - 1].rango = [a.precio, a.precio];
    data.push({ semana: next, rango: [a.precio_min_esperado, a.precio_max_esperado] });
  }

  return (
    <div className="detail">
      <div className="detail-head">
        <h2 id="detail-title"><Photo name={a.producto} className="thumb" /> {a.producto}</h2>
        <button className="close" onClick={onClose} aria-label="Cerrar">×</button>
      </div>
      <p><span className={action.className}>{action.text}</span></p>
      <p className="detail-text">
        El último precio en Cavasa fue <strong>{pesos(a.precio)}/kg</strong> (semana del {day(a.semana_inicio)}):{" "}
        {a.cambio_1s > 0 ? "subió" : "bajó"} {pct(a.cambio_1s)} frente a la semana anterior.
        {a.weak
          ? <>Para la semana del {day(next)} no hay una señal clara: el modelo se inclina por que {ACTION[a.modelo].why.replace("se espera que ", "")}, pero con poca confianza ({Math.round(a.confianza * 100)} %). Por eso la recomendación es comprar como siempre. </>
          : <>Para la semana del {day(next)} {a.prediccion === "estable" ? "no se espera un cambio importante" : action.why}: </>}
        entre <strong>{pesos(a.precio_min_esperado)}</strong> y{" "}
        <strong>{pesos(a.precio_max_esperado)}</strong> por kilo.
        {a.evaluadas ? ` Con este producto el modelo acertó ${a.aciertos} de las últimas ${a.evaluadas} semanas.` : ""}
      </p>
      {history === null && <p className="muted">Cargando precios…</p>}
      {history?.length === 0 && <p className="muted">No hay historial de precios para mostrar.</p>}
      {data.length > 0 && (
        <>
          <h3>Últimos 6 meses y lo que viene</h3>
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={data} margin={{ left: 4, right: 12, top: 8 }}>
              <CartesianGrid stroke="var(--line)" vertical={false} />
              <XAxis dataKey="semana" tickFormatter={(d) => day(d)} tick={{ fontSize: 12, fill: "var(--muted)" }} minTickGap={36} />
              <YAxis tickFormatter={(v) => "$" + (v / 1000).toLocaleString("es-CO") + " mil"} tick={{ fontSize: 12, fill: "var(--muted)" }} width={68} domain={["auto", "auto"]} />
              <Tooltip
                labelFormatter={(d) => "Semana del " + day(d)}
                formatter={(v, name) => [Array.isArray(v) ? `${pesos(v[0])} – ${pesos(v[1])}` : pesos(v), name]}
                contentStyle={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: 8 }}
              />
              <Area dataKey="rango" name="Rango esperado" stroke="none" fill="var(--mist)" fillOpacity={0.7} />
              <Line dataKey="nacional" name="Mediana nacional" stroke="var(--muted)" strokeDasharray="4 4" dot={false} />
              <Line dataKey="precio" name="Cavasa" stroke="var(--forest)" strokeWidth={2.5} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
          <p className="legend small muted">
            <span className="key cavasa" /> Cavasa <span className="key dashed" /> Mediana nacional <span className="key rango" /> Rango esperado para la próxima semana
          </p>
        </>
      )}
    </div>
  );
}
