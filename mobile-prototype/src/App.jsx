import { Fragment, useRef, useState } from 'react'
import {
    DndContext,
    DragOverlay,
    MouseSensor,
    TouchSensor,
    closestCenter,
    pointerWithin,
    useDraggable,
    useDroppable,
    useSensor,
    useSensors,
} from '@dnd-kit/core'
import {
    SortableContext,
    arrayMove,
    useSortable,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { initialDevices, initialScenarios } from './mock'

let counter = 100
const uid = (p) => `${p}${counter++}`
const split = (id) => String(id).split(':')
const scenarioOfBlock = (list, blockId) =>
    list.find((s) => s.blocks.some((b) => b.id === blockId))

const columnsOf = (blocks) => {
    const map = new Map()
    blocks.forEach((b, i) => {
        const c = b.col ?? i
        if (!map.has(c)) map.set(c, [])
        map.get(c).push(b)
    })
    return [...map.entries()].sort((a, b) => a[0] - b[0]).map(([, list]) => list)
}
const fromColumns = (cols) => cols.flatMap((list, ci) => list.map((b) => ({ ...b, col: ci })))
const normalizeBlocks = (blocks) => fromColumns(columnsOf(blocks))

const noShift = () => null
const collide = (args) => {
    if (String(args.active.id).startsWith('scenario:')) {
        return closestCenter({
            ...args,
            droppableContainers: args.droppableContainers.filter((c) =>
                String(c.id).startsWith('scenario:'),
            ),
        })
    }
    const hits = pointerWithin(args)
    return hits.length ? hits : closestCenter(args)
}

const situations = [
    { type: 'water', label: 'Отключили воду' },
    { type: 'power', label: 'Нет электричества' },
    { type: 'gas', label: 'Отключили газ' },
    { type: 'internet', label: 'Нет интернета' },
    { type: 'heating', label: 'Отключили отопление' },
    { type: 'door', label: 'Открыта дверь' },
    { type: 'away', label: 'Никого нет дома' },
    { type: 'leak', label: 'Протечка', noTime: true },
    { type: 'smoke', label: 'Дым в помещении', noTime: true },
    { type: 'night', label: 'Наступила ночь', noTime: true },
    { type: 'cold', label: 'Температура ниже', unit: '°C', value: 18 },
    { type: 'hot', label: 'Температура выше', unit: '°C', value: 28 },
]
const situationOf = (type, list) => list.find((s) => s.type === type)

const paramTypes = [
    { type: 'switch', label: 'Вкл / выкл' },
    { type: 'counter', label: 'Число' },
    { type: 'list', label: 'Список' },
    { type: 'color', label: 'Цвет' },
    { type: 'text', label: 'Текст' },
]

const P = (id, label, type, access, value, extra = {}) => ({ id, label, type, access, value, ...extra })

const asParam = (p) =>
    typeof p === 'string' ? { id: p, label: p, type: 'text', access: 'r', value: '' } : p
const canWrite = (p) => String(p.access ?? 'r').includes('w')

const paramValueText = (p) => {
    const v = p.value
    if (p.type === 'switch') return v ? 'Вкл' : 'Выкл'
    if (p.type === 'list') return p.layout?.[v] ?? String(v)
    if (p.type === 'counter') return `${v}${p.unit ? ` ${p.unit}` : ''}`
    return String(v ?? '')
}
const paramLine = (p) =>
    p.type === 'text' && p.value === '' ? p.label : `${p.label}: ${paramValueText(p)}`

const clampNum = (v, p) => {
    let n = Number(v)
    if (!Number.isFinite(n)) n = p.min ?? 0
    if (p.min != null) n = Math.max(p.min, n)
    if (p.max != null) n = Math.min(p.max, n)
    return n
}

const barrierStates = { 0: 'закрыто', 1: 'открывается', 2: 'открыто', 3: 'закрывается', 4: 'удержание' }

const deviceCatalog = [
    {
        key: 'leak',
        name: 'Датчик протечки',
        params: [
            P('state', 'Состояние', 'list', 'r', 0, { layout: { 0: 'сухо', 1: 'протечка' } }),
            P('battery', 'Заряд', 'counter', 'r', 100, { unit: '%', min: 0, max: 100 }),
            P('sensitivity', 'Чувствительность', 'counter', 'rw', 5, { min: 1, max: 10 }),
        ],
    },
    {
        key: 'barrier',
        name: 'Шлагбаум',
        params: [
            P('open_cmd', 'Открыть', 'switch', 'rw', 0),
            P('hold_time', 'Держать открытым', 'counter', 'rw', 10, { unit: 'c', min: 0, max: 300 }),
            P('state', 'Состояние стрелы', 'list', 'r', 0, { layout: barrierStates }),
            P('obstacle', 'Предмет под стрелой', 'list', 'r', 0, { layout: { 0: 'нет', 1: 'есть' } }),
            P('alarm', 'Авария', 'list', 'r', 0, { layout: { 0: 'нет', 1: 'застревание' } }),
            P('cycles', 'Циклов открытий', 'counter', 'r', 0),
        ],
    },
    {
        key: 'thermostat',
        name: 'Термостат',
        params: [
            P('target', 'Нужная температура', 'counter', 'rw', 22, { unit: '°C', min: 16, max: 30 }),
            P('current', 'Сейчас', 'counter', 'r', 21, { unit: '°C' }),
            P('mode', 'Режим', 'list', 'rw', 2, { layout: { 0: 'выкл', 1: 'нагрев', 2: 'авто' } }),
        ],
    },
    {
        key: 'elevator',
        name: 'Лифт',
        params: [
            P('call', 'Вызвать на этаж', 'counter', 'rw', 1, { min: 1, max: 25 }),
            P('floor', 'Текущий этаж', 'counter', 'r', 1),
            P('state', 'Состояние', 'list', 'r', 0, { layout: { 0: 'стоит', 1: 'едет', 2: 'двери открыты' } }),
        ],
    },
    {
        key: 'hub',
        name: 'Хаб протечек',
        params: [
            P('siren', 'Сирена', 'switch', 'rw', 1),
            P('count', 'Датчиков подключено', 'counter', 'r', 0),
            P('state', 'Состояние', 'list', 'r', 0, { layout: { 0: 'норма', 1: 'протечка' } }),
        ],
    },
    {
        key: 'counter',
        name: 'Счётчик',
        params: [
            P('send', 'Передавать показания', 'switch', 'rw', 1),
            P('reading', 'Показания', 'counter', 'r', 0, { unit: 'м³' }),
        ],
    },
    {
        key: 'ventilation',
        name: 'Вентиляция',
        params: [
            P('speed', 'Скорость', 'counter', 'rw', 2, { min: 1, max: 3 }),
            P('mode', 'Режим', 'list', 'rw', 0, { layout: { 0: 'авто', 1: 'ручной' } }),
        ],
    },
    {
        key: 'fire',
        name: 'Датчик пожара',
        params: [
            P('sensitivity', 'Чувствительность', 'counter', 'rw', 3, { min: 1, max: 5 }),
            P('smoke', 'Уровень дыма', 'counter', 'r', 0, { unit: '%' }),
            P('state', 'Состояние', 'list', 'r', 0, { layout: { 0: 'норма', 1: 'пожар' } }),
        ],
    },
    {
        key: 'light',
        name: 'Освещение',
        params: [
            P('brightness', 'Яркость', 'counter', 'rw', 80, { unit: '%', min: 0, max: 100 }),
            P('color', 'Цвет', 'color', 'rw', '#ffd9a0'),
        ],
    },
]

const catalogRules = [
    ['hub', /хаб/],
    ['leak', /протеч/],
    ['barrier', /шлагбаум/],
    ['thermostat', /термостат|температур|отоплен|климат|тёплый пол|теплый пол/],
    ['elevator', /лифт/],
    ['counter', /счётчик|счетчик/],
    ['ventilation', /вентиля|кондиционер/],
    ['fire', /пожар|дым/],
    ['light', /ламп|свет|освещ|торшер|люстр/],
]

const legacyParam = (str, i) => {
    const [label, ...rest] = String(str).split(':')
    return {
        id: `legacy${i}`,
        label: rest.length ? label.trim() : String(str),
        type: 'text',
        access: 'rw',
        value: rest.join(':').trim(),
    }
}

const upgradeDevice = (d) => {
    const params = d.params ?? []
    if (params.length > 0 && params.every((p) => typeof p !== 'string')) return d
    const key = catalogRules.find(([, re]) => re.test(String(d.name).toLowerCase()))?.[0]
    const item = deviceCatalog.find((x) => x.key === key)
    if (item) return { ...d, params: item.params.map((p) => ({ ...p })) }
    return { ...d, params: params.map(legacyParam) }
}

const reactions = [
    { type: 'off', label: 'Выключить устройства сценария' },
    { type: 'on', label: 'Включить устройства сценария' },
    { type: 'notify', label: 'Прислать уведомление' },
    { type: 'support', label: 'Обратиться в техподдержку' },
    { type: 'none', label: 'Ничего не делать' },
    { type: 'custom', label: 'Своё действие' },
]

const reactionText = (c) => {
    const r = reactions.find((x) => x.type === (c.action ?? 'off'))
    if (!r) return ''
    if (r.type === 'custom') return c.actionText?.trim() || 'Своё действие'
    return r.label
}

const supportTopics = [
    'Устройство не работает',
    'Не срабатывает сценарий',
    'Вопрос по ситуациям',
    'Другое',
]

const condText = (c, list) => {
    const s = situationOf(c.type, list)
    if (!s) return '?'
    let text = s.label
    if (s.unit && c.value !== '' && c.value != null) text += ` ${c.value}${s.unit}`
    if (c.time) text += ` в ${c.time}`
    return text
}

const plural = (n, forms) => {
    const a = Math.abs(n) % 100
    const b = a % 10
    if (a > 10 && a < 20) return forms[2]
    if (b > 1 && b < 5) return forms[1]
    if (b === 1) return forms[0]
    return forms[2]
}

const durationText = (e) =>
    e.unit === 'd'
        ? `${e.amount} ${plural(e.amount, ['день', 'дня', 'дней'])}`
        : `${e.amount} ${plural(e.amount, ['час', 'часа', 'часов'])}`

function HomePage({
    devices,
    scenarios,
    emergencies,
    sits,
    tickets,
    onStart,
    onEnd,
    onTicket,
    onCloseTicket,
}) {
    const options = sits.filter((s) => !s.unit && s.type !== 'night')
    const [type, setType] = useState(options[0]?.type ?? '__custom')
    const [name, setName] = useState('')
    const [amount, setAmount] = useState(2)
    const [unit, setUnit] = useState('d')
    const [topic, setTopic] = useState(supportTopics[0])
    const [ticketDevice, setTicketDevice] = useState('')
    const [ticketText, setTicketText] = useState('')
    const openTickets = tickets.filter((t) => !t.done).length

    const sendTicket = () => {
        onTicket({ subject: topic, deviceId: ticketDevice || null, text: ticketText.trim() })
        setTicketText('')
    }

    const custom = type === '__custom'
    const canStart = Number(amount) >= 1 && (!custom || name.trim().length > 0)
    const onCount = devices.filter((d) => d.on).length
    const affected = (e) =>
        scenarios
            .map((s) => ({ s, c: (s.conditions ?? []).find((c) => c.type === e.type) }))
            .filter((x) => x.c)
    const hasAlerts = emergencies.length > 0

    const start = () => {
        onStart({ type, name, amount: Number(amount), unit })
        if (custom) setName('')
    }

    return (
        <>
            <section className="card panel">
                <h2>Квартира №</h2>
                <div className="stats">
                    <div className="stat">
                        <b>
                            {onCount} / {devices.length}
                        </b>
                        <span>устройств включено</span>
                    </div>
                    <div className="stat">
                        <b>{scenarios.length}</b>
                        <span>{plural(scenarios.length, ['сценарий', 'сценария', 'сценариев'])}</span>
                    </div>
                </div>
            </section>

            <section className={`card panel ${hasAlerts ? 'alert' : ''}`}>
                <div className="status">
                    <h2>Аварийные ситуации</h2>
                    <span className="status-value">{hasAlerts ? 'Есть' : 'Нет'}</span>
                </div>

                {!hasAlerts && <span className="hint">Всё в порядке, ничего не происходит</span>}

                {emergencies.map((e) => {
                    const list = affected(e)
                    return (
                        <div key={e.id} className="emergency">
                            <div>
                                <div className="emergency-name">
                                    {e.label} на {durationText(e)}
                                </div>
                                <div className="emergency-sub">
                                    {list.length > 0
                                        ? list.map(({ s, c }) => `${s.title}: ${reactionText(c)}`).join('; ')
                                        : 'Сценарии не затронуты'}
                                </div>
                            </div>
                            <button onClick={() => onEnd(e.id)}>Завершить</button>
                        </div>
                    )
                })}
            </section>

            <section className="card panel">
                <h2>Эмуляция ситуации</h2>

                <label className="field">
                    Что случилось
                    <select value={type} onChange={(e) => setType(e.target.value)}>
                        {options.map((s) => (
                            <option key={s.type} value={s.type}>
                                {s.label}
                            </option>
                        ))}
                        <option value="__custom">Создать свою ситуацию</option>
                    </select>
                </label>

                {custom && (
                    <label className="field">
                        Название ситуации
                        <input
                            value={name}
                            maxLength={40}
                            placeholder="Например, Сломался лифт"
                            onChange={(e) => setName(e.target.value)}
                        />
                    </label>
                )}

                <div className="row">
                    <label className="field">
                        Длительность
                        <input
                            type="number"
                            inputMode="numeric"
                            min="1"
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                        />
                    </label>
                    <label className="field">
                        Единицы
                        <select value={unit} onChange={(e) => setUnit(e.target.value)}>
                            <option value="h">часов</option>
                            <option value="d">дней</option>
                        </select>
                    </label>
                </div>

                <button className="btn" disabled={!canStart} onClick={start}>
                    Запустить
                </button>
            </section>

            <section className="card panel">
                <div className="status">
                    <h2>Техподдержка</h2>
                    <span className="status-value">{openTickets > 0 ? openTickets : 'Нет проблем'}</span>
                </div>

                {tickets.length === 0 && <span className="hint">Открытых обращений нет</span>}

                {tickets.slice(0, 5).map((t) => {
                    const dev = devices.find((d) => d.id === t.deviceId)
                    return (
                        <div key={t.id} className={`ticket ${t.done ? 'done' : ''}`}>
                            <div>
                                <div className="ticket-name">{t.subject}</div>
                                <div className="ticket-sub">
                                    {[dev?.name, t.text, t.auto ? 'Создано сценарием' : null]
                                        .filter(Boolean)
                                        .join(' · ')}
                                </div>
                            </div>
                            {t.done ? (
                                <span className="hint">Закрыто</span>
                            ) : (
                                <button onClick={() => onCloseTicket(t.id)}>Закрыть</button>
                            )}
                        </div>
                    )
                })}

                <label className="field">
                    Тема
                    <select value={topic} onChange={(e) => setTopic(e.target.value)}>
                        {supportTopics.map((t) => (
                            <option key={t} value={t}>
                                {t}
                            </option>
                        ))}
                    </select>
                </label>

                <label className="field">
                    Устройство (необязательно)
                    <select value={ticketDevice} onChange={(e) => setTicketDevice(e.target.value)}>
                        <option value="">Не выбрано</option>
                        {devices.map((d) => (
                            <option key={d.id} value={d.id}>
                                {d.name}
                            </option>
                        ))}
                    </select>
                </label>

                <label className="field">
                    Что случилось
                    <input
                        value={ticketText}
                        maxLength={120}
                        placeholder="Опишите проблему"
                        onChange={(e) => setTicketText(e.target.value)}
                    />
                </label>

                <button className="btn" disabled={ticketText.trim().length === 0} onClick={sendTicket}>
                    Написать в техподдержку
                </button>
            </section>
        </>
    )
}

function DeviceCard({ device, onToggle, onRemove, onEdit }) {
    const params = (device.params ?? []).map(asParam)
    const shown = params.slice(0, 3)
    const rest = params.length - shown.length
    return (
        <article className={`card device ${device.on ? 'is-on' : ''}`} onClick={() => onEdit(device.id)}>
            <div className="device-top">
                <span className="device-state">{device.on ? 'Включено' : 'Выключено'}</span>
                <button
                    className="toggle"
                    role="switch"
                    aria-checked={device.on}
                    aria-label={`Переключить ${device.name}`}
                    onClick={(e) => {
                        e.stopPropagation()
                        onToggle(device.id)
                    }}
                >
                    <span className="knob" />
                </button>
            </div>

            <div className="device-head">
                <h2 className="device-name">{device.name}</h2>
                {device.ujin && <span className="ujin">Ujin</span>}
            </div>

            <ul className="params">
                {shown.map((p) => (
                    <li key={p.id}>{paramLine(p)}</li>
                ))}
                {rest > 0 && <li>ещё {rest}</li>}
            </ul>

            <button
                className="link"
                onClick={(e) => {
                    e.stopPropagation()
                    onRemove(device.id)
                }}
            >
                Удалить
            </button>
        </article>
    )
}

function DevicesPage({ devices, onToggle, onRemove, onAdd, onEdit }) {
    return (
        <>
            {devices.length === 0 && <p className="empty">Устройств пока нет</p>}
            <div className="device-list">
                {devices.map((d) => (
                    <DeviceCard key={d.id} device={d} onToggle={onToggle} onRemove={onRemove} onEdit={onEdit} />
                ))}
            </div>
            <button className="card add" onClick={onAdd}>
                Добавить новое устройство +
            </button>
        </>
    )
}

function ParamField({ p, onChange }) {
    if (p.type === 'switch') {
        return (
            <div className="param-row">
                <span>{p.label}</span>
                <button
                    className="toggle"
                    role="switch"
                    aria-checked={!!p.value}
                    aria-label={p.label}
                    onClick={() => onChange(p.value ? 0 : 1)}
                >
                    <span className="knob" />
                </button>
            </div>
        )
    }
    if (p.type === 'list') {
        return (
            <label className="field">
                {p.label}
                <select value={p.value} onChange={(e) => onChange(Number(e.target.value))}>
                    {Object.entries(p.layout ?? {}).map(([k, label]) => (
                        <option key={k} value={k}>
                            {label}
                        </option>
                    ))}
                </select>
            </label>
        )
    }
    if (p.type === 'counter') {
        return (
            <label className="field">
                {p.label}
                {p.unit ? `, ${p.unit}` : ''}
                {p.min != null && p.max != null ? ` (${p.min}–${p.max})` : ''}
                <input
                    type="number"
                    inputMode="numeric"
                    min={p.min}
                    max={p.max}
                    value={p.value}
                    onChange={(e) => onChange(e.target.value)}
                />
            </label>
        )
    }
    return (
        <label className="field">
            {p.label}
            <input
                type={p.type === 'color' ? 'color' : 'text'}
                value={p.value ?? ''}
                maxLength={60}
                onChange={(e) => onChange(e.target.value)}
            />
        </label>
    )
}

function DeviceSheet({ device, onSave, onClose }) {
    const [params, setParams] = useState(() => (device.params ?? []).map((p) => ({ ...asParam(p) })))
    const setValue = (id, value) =>
        setParams((ps) => ps.map((p) => (p.id === id ? { ...p, value } : p)))

    const editable = params.filter((p) => canWrite(p))
    const readonly = params.filter((p) => !canWrite(p))

    const save = () =>
        onSave(
            device.id,
            params.map((p) => (p.type === 'counter' ? { ...p, value: clampNum(p.value, p) } : p)),
        )

    return (
        <div className="backdrop" onClick={onClose}>
            <div className="sheet" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
                <div className="device-head">
                    <h3>{device.name}</h3>
                    {device.ujin && <span className="ujin">Ujin</span>}
                </div>
                <p className="sheet-sub">Изменения применяются ко всем сценариям с этим устройством</p>

                {params.length === 0 && <span className="hint">У устройства нет параметров</span>}

                {editable.length > 0 && <div className="sheet-part">Параметры</div>}
                {editable.map((p) => (
                    <ParamField key={p.id} p={p} onChange={(v) => setValue(p.id, v)} />
                ))}

                {readonly.length > 0 && <div className="sheet-part">Только чтение</div>}
                {readonly.map((p) => (
                    <div key={p.id} className="param-row ro">
                        <span>{p.label}</span>
                        {!(p.type === 'text' && p.value === '') && <span>{paramValueText(p)}</span>}
                    </div>
                ))}

                <div className="sheet-actions">
                    <button onClick={onClose}>Отмена</button>
                    <button className="btn-primary" onClick={save}>
                        Сохранить
                    </button>
                </div>
            </div>
        </div>
    )
}

const newRow = () => ({
    key: uid('r'),
    label: '',
    type: 'switch',
    unit: '',
    min: '',
    max: '',
    options: '',
    value: '',
})

const rowOk = (r) =>
    r.label.trim().length > 0 &&
    (r.type !== 'list' || r.options.split(',').filter((x) => x.trim()).length >= 2)

const buildParam = (r) => {
    const base = { id: uid('p'), label: r.label.trim(), type: r.type, access: 'rw' }
    if (r.type === 'switch') return { ...base, value: 0 }
    if (r.type === 'color') return { ...base, value: '#ffffff' }
    if (r.type === 'text') return { ...base, value: r.value.trim() }
    if (r.type === 'list') {
        const opts = r.options
            .split(',')
            .map((x) => x.trim())
            .filter(Boolean)
        return { ...base, value: 0, layout: Object.fromEntries(opts.map((o, i) => [i, o])) }
    }
    const min = r.min === '' ? undefined : Number(r.min)
    const max = r.max === '' ? undefined : Number(r.max)
    const p = { ...base, unit: r.unit.trim() || undefined, min, max }
    return { ...p, value: clampNum(0, p) }
}

function AddDeviceSheet({ onSave, onClose }) {
    const [mode, setMode] = useState('catalog')
    const [key, setKey] = useState(deviceCatalog[0].key)
    const [name, setName] = useState('')
    const [rows, setRows] = useState([])

    const custom = mode === 'custom'
    const item = deviceCatalog.find((d) => d.key === key)
    const canSave = !custom || (name.trim().length > 0 && rows.every(rowOk))

    const patch = (k, data) => setRows((rs) => rs.map((r) => (r.key === k ? { ...r, ...data } : r)))

    const save = () =>
        custom
            ? onSave({ name: name.trim(), params: rows.map(buildParam), ujin: false })
            : onSave({ name: item.name, params: item.params.map((p) => ({ ...p })), ujin: true })

    return (
        <div className="backdrop" onClick={onClose}>
            <div className="sheet" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
                <h3>Добавить устройство</h3>

                <div className="dock-tabs sheet-tabs">
                    <button className={!custom ? 'active' : ''} onClick={() => setMode('catalog')}>
                        Из списка
                    </button>
                    <button className={custom ? 'active' : ''} onClick={() => setMode('custom')}>
                        Своё
                    </button>
                </div>

                {!custom && (
                    <>
                        <label className="field">
                            Устройство
                            <select value={key} onChange={(e) => setKey(e.target.value)}>
                                {deviceCatalog.map((d) => (
                                    <option key={d.key} value={d.key}>
                                        {d.name}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <ul className="params">
                            {item.params.map((p) => (
                                <li key={p.id}>{paramLine(p)}</li>
                            ))}
                        </ul>
                        <div className="sheet-ujin">
                            <span className="ujin">Ujin</span>
                            Устройство одобрено и подтягивается из Ujin
                        </div>
                    </>
                )}

                {custom && (
                    <>
                        <label className="field">
                            Название
                            <input
                                autoFocus
                                value={name}
                                maxLength={40}
                                placeholder="Например, Умная розетка"
                                onChange={(e) => setName(e.target.value)}
                            />
                        </label>

                        <div className="sheet-part">Параметры</div>

                        {rows.length === 0 && <span className="hint">Параметров пока нет</span>}

                        {rows.map((r, i) => (
                            <div key={r.key} className="param-draft">
                                <div className="param-draft-head">
                                    <span>Параметр {i + 1}</span>
                                    <button
                                        className="x"
                                        onClick={() => setRows((rs) => rs.filter((x) => x.key !== r.key))}
                                        aria-label="Убрать параметр"
                                    >
                                        ×
                                    </button>
                                </div>

                                <label className="field">
                                    Название
                                    <input
                                        value={r.label}
                                        maxLength={30}
                                        placeholder="Например, Яркость"
                                        onChange={(e) => patch(r.key, { label: e.target.value })}
                                    />
                                </label>

                                <label className="field">
                                    Тип
                                    <select value={r.type} onChange={(e) => patch(r.key, { type: e.target.value })}>
                                        {paramTypes.map((t) => (
                                            <option key={t.type} value={t.type}>
                                                {t.label}
                                            </option>
                                        ))}
                                    </select>
                                </label>

                                {r.type === 'counter' && (
                                    <div className="row">
                                        <label className="field">
                                            Единицы
                                            <input
                                                value={r.unit}
                                                maxLength={6}
                                                placeholder="%"
                                                onChange={(e) => patch(r.key, { unit: e.target.value })}
                                            />
                                        </label>
                                        <label className="field">
                                            Мин
                                            <input
                                                type="number"
                                                inputMode="numeric"
                                                value={r.min}
                                                onChange={(e) => patch(r.key, { min: e.target.value })}
                                            />
                                        </label>
                                        <label className="field">
                                            Макс
                                            <input
                                                type="number"
                                                inputMode="numeric"
                                                value={r.max}
                                                onChange={(e) => patch(r.key, { max: e.target.value })}
                                            />
                                        </label>
                                    </div>
                                )}

                                {r.type === 'list' && (
                                    <label className="field">
                                        Варианты через запятую (минимум два)
                                        <input
                                            value={r.options}
                                            maxLength={80}
                                            placeholder="Тихо, Средне, Громко"
                                            onChange={(e) => patch(r.key, { options: e.target.value })}
                                        />
                                    </label>
                                )}

                                {r.type === 'text' && (
                                    <label className="field">
                                        Значение
                                        <input
                                            value={r.value}
                                            maxLength={60}
                                            onChange={(e) => patch(r.key, { value: e.target.value })}
                                        />
                                    </label>
                                )}
                            </div>
                        ))}

                        <button className="sheet-add" onClick={() => setRows((rs) => [...rs, newRow()])}>
                            Добавить параметр +
                        </button>

                        <span className="hint">Своё устройство не одобрено Ujin</span>
                    </>
                )}

                <div className="sheet-actions">
                    <button onClick={onClose}>Отмена</button>
                    <button className="btn-primary" disabled={!canSave} onClick={save}>
                        Добавить
                    </button>
                </div>
            </div>
        </div>
    )
}

function DockChip({ device, wide }) {
    const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
        id: `device:${device.id}`,
    })
    return (
        <div
            ref={setNodeRef}
            className={`chip ${wide ? 'wide' : ''} ${isDragging ? 'ghost' : ''}`}
            {...attributes}
            {...listeners}
        >
            <span className={`dot ${device.on ? 'on' : ''}`} />
            {device.name}
        </div>
    )
}

function SituationChip({ situation, wide }) {
    const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
        id: `cond:${situation.type}`,
    })
    return (
        <div
            ref={setNodeRef}
            className={`chip ${wide ? 'wide' : ''} ${isDragging ? 'ghost' : ''}`}
            {...attributes}
            {...listeners}
        >
            {situation.label}
        </div>
    )
}

function Block({ block, device, onRemove, onEdit }) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
        useSortable({ id: `block:${block.id}` })
    return (
        <div
            ref={setNodeRef}
            className={`block ${isDragging ? 'ghost' : ''}`}
            style={{ transform: CSS.Transform.toString(transform), transition }}
            {...attributes}
            {...listeners}
            onClick={() => device && onEdit(device.id)}
        >
            <span className={`dot ${device?.on ? 'on' : ''}`} />
            <span>{device?.name ?? '?'}</span>
            <button
                className="x"
                onClick={(e) => {
                    e.stopPropagation()
                    onRemove(block.id)
                }}
                aria-label="Убрать из сценария"
            >
                ×
            </button>
        </div>
    )
}

function Column({ id, children }) {
    const { setNodeRef } = useDroppable({ id })
    return (
        <div ref={setNodeRef} className="gcol">
            {children}
        </div>
    )
}

function Gap({ id, last }) {
    const { setNodeRef, isOver } = useDroppable({ id })
    return (
        <div ref={setNodeRef} className={`gap ${last ? 'last' : ''} ${isOver ? 'over' : ''}`}>
            {last ? '+' : ''}
        </div>
    )
}

function Scenario({
    scenario,
    devices,
    sits,
    onRename,
    onRemoveBlock,
    onRemove,
    onAddCond,
    onEditCond,
    onRemoveCond,
    onEditDevice,
}) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
        useSortable({ id: `scenario:${scenario.id}` })
    const inputRef = useRef(null)
    const conditions = scenario.conditions ?? []
    const columns = columnsOf(scenario.blocks)
    return (
        <section
            ref={setNodeRef}
            className={`card scenario ${isDragging ? 'ghost' : ''}`}
            style={{ transform: CSS.Transform.toString(transform), transition }}
        >
            <header className="scenario-head">
                <button className="handle" {...attributes} {...listeners} aria-label="Переместить сценарий">
                    *
                </button>
                <input
                    ref={inputRef}
                    value={scenario.title}
                    maxLength={40}
                    placeholder="Название сценария"
                    onChange={(e) => onRename(scenario.id, e.target.value)}
                    onBlur={(e) => {
                        if (!e.target.value.trim()) onRename(scenario.id, 'Без названия')
                    }}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') e.currentTarget.blur()
                    }}
                    aria-label="Название сценария"
                />
                <button
                    className="x edit"
                    onClick={() => {
                        inputRef.current?.focus()
                        inputRef.current?.select()
                    }}
                    aria-label="Переименовать сценарий"
                >
                    ✎
                </button>
                <button className="x" onClick={() => onRemove(scenario.id)} aria-label="Удалить сценарий">
                    ×
                </button>
            </header>

            <div className="conds-title gantt-hint">
                Рядом - по очереди, друг под другом - одновременно
            </div>

            <div className="blocks gantt">
                <SortableContext items={columns.flat().map((b) => `block:${b.id}`)} strategy={noShift}>
                    {columns.map((col, ci) => (
                        <Fragment key={ci}>
                            <Gap id={`gap:${scenario.id}:${ci}`} />
                            <Column id={`col:${scenario.id}:${ci}`}>
                                {col.map((b) => (
                                    <Block
                                        key={b.id}
                                        block={b}
                                        device={devices.find((d) => d.id === b.deviceId)}
                                        onRemove={onRemoveBlock}
                                        onEdit={onEditDevice}
                                    />
                                ))}
                            </Column>
                        </Fragment>
                    ))}
                    {scenario.blocks.length === 0 && (
                        <span className="hint">Необходимо перенести устройство из панели внизу</span>
                    )}
                    <Gap id={`gap:${scenario.id}:${columns.length}`} last />
                </SortableContext>
            </div>

            <div className="conds">
                <div className="conds-title">Ситуации, влияющие на сценарий</div>
                <div className="conds-list">
                    {conditions.map((c) => (
                        <div key={c.id} className="cond-wrap">
                            <button className="cond" onClick={() => onEditCond(scenario.id, c.id)}>
                                <span className="cond-if">Если: {condText(c, sits)}</span>
                                <span className="cond-then">То: {reactionText(c)}</span>
                            </button>
                            <button
                                className="x cond-x"
                                onClick={() => onRemoveCond(scenario.id, c.id)}
                                aria-label="Удалить ситуацию"
                            >
                                ×
                            </button>
                        </div>
                    ))}
                    <button className="cond cond-add" onClick={() => onAddCond(scenario.id)}>
                        + Ситуация
                    </button>
                </div>
                {conditions.length === 0 && (
                    <span className="hint">Перетащи ситуацию из панели внизу или нажми «+ Ситуация»</span>
                )}
            </div>
        </section>
    )
}

function ScenariosPage({
    scenarios,
    devices,
    sits,
    onRename,
    onRemoveBlock,
    onRemove,
    onAdd,
    onAddCond,
    onEditCond,
    onRemoveCond,
    onEditDevice,
}) {
    return (
        <>
            <SortableContext
                items={scenarios.map((s) => `scenario:${s.id}`)}
                strategy={verticalListSortingStrategy}
            >
                {scenarios.map((s) => (
                    <Scenario
                        key={s.id}
                        scenario={s}
                        devices={devices}
                        sits={sits}
                        onRename={onRename}
                        onRemoveBlock={onRemoveBlock}
                        onRemove={onRemove}
                        onAddCond={onAddCond}
                        onEditCond={onEditCond}
                        onRemoveCond={onRemoveCond}
                        onEditDevice={onEditDevice}
                    />
                ))}
            </SortableContext>
            <button className="card add" onClick={onAdd}>
                Создать новый сценарий +
            </button>
        </>
    )
}

function ConditionSheet({ sheet, scenarios, sits, onSave, onDelete, onClose }) {
    const scenario = scenarios.find((s) => s.id === sheet.scenarioId)
    const existing =
        sheet.mode === 'edit' ? (scenario?.conditions ?? []).find((c) => c.id === sheet.condId) : null

    const [type, setType] = useState(existing?.type ?? sits[0].type)
    const [time, setTime] = useState(existing?.time ?? '')
    const [value, setValue] = useState(
        existing?.value ?? situationOf(existing?.type ?? sits[0].type, sits)?.value ?? '',
    )
    const [newName, setNewName] = useState('')
    const [action, setAction] = useState(existing?.action ?? 'off')
    const [actionText, setActionText] = useState(existing?.actionText ?? '')

    const isNew = type === '__new'
    const sit = situationOf(type, sits)
    const canSave =
        (!isNew || newName.trim().length > 0) && (action !== 'custom' || actionText.trim().length > 0)

    const changeType = (t) => {
        setType(t)
        setValue(situationOf(t, sits)?.value ?? '')
        if (situationOf(t, sits)?.noTime) setTime('')
    }

    return (
        <div className="backdrop" onClick={onClose}>
            <div className="sheet" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
                <h3>{existing ? 'Ситуация' : 'Добавить ситуацию'}</h3>
                <p className="sheet-sub">Сценарий: {scenario?.title}</p>

                <div className="sheet-part">Если</div>

                <label className="field">
                    Что произошло
                    <select value={type} onChange={(e) => changeType(e.target.value)}>
                        {sits.map((s) => (
                            <option key={s.type} value={s.type}>
                                {s.label}
                            </option>
                        ))}
                        <option value="__new">Своя ситуация +</option>
                    </select>
                </label>

                {isNew && (
                    <label className="field">
                        Название ситуации
                        <input
                            value={newName}
                            maxLength={40}
                            placeholder="Например, Сломался лифт"
                            onChange={(e) => setNewName(e.target.value)}
                        />
                    </label>
                )}

                {sit?.unit && (
                    <label className="field">
                        Порог, {sit.unit}
                        <input
                            type="number"
                            inputMode="numeric"
                            value={value}
                            onChange={(e) => setValue(e.target.value)}
                        />
                    </label>
                )}

                {!sit?.noTime && (
                    <label className="field">
                        Во сколько (необязательно)
                        <input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
                    </label>
                )}

                <div className="sheet-part">То</div>

                <label className="field">
                    Что произойдёт
                    <select value={action} onChange={(e) => setAction(e.target.value)}>
                        {reactions.map((r) => (
                            <option key={r.type} value={r.type}>
                                {r.label}
                            </option>
                        ))}
                    </select>
                </label>

                {action === 'custom' && (
                    <label className="field">
                        Опиши действие
                        <input
                            value={actionText}
                            maxLength={60}
                            placeholder="Например, Закрыть кран"
                            onChange={(e) => setActionText(e.target.value)}
                        />
                    </label>
                )}

                <div className="sheet-actions">
                    <button onClick={onClose}>Отмена</button>
                    {existing && (
                        <button className="btn-danger" onClick={onDelete}>
                            Удалить
                        </button>
                    )}
                    <button
                        className="btn-primary"
                        disabled={!canSave}
                        onClick={() =>
                            onSave({
                                type,
                                newLabel: isNew ? newName : undefined,
                                time: sit?.noTime ? '' : time,
                                value: sit?.unit ? value : '',
                                action,
                                actionText: action === 'custom' ? actionText : '',
                            })
                        }
                    >
                        Сохранить
                    </button>
                </div>
            </div>
        </div>
    )
}

function NewSituationSheet({ onSave, onClose }) {
    const [name, setName] = useState('')
    const ok = name.trim().length > 0
    return (
        <div className="backdrop" onClick={onClose}>
            <div className="sheet" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
                <h3>Своя ситуация</h3>
                <p className="sheet-sub">Она появится в панели «Ситуации» и в списках выбора</p>

                <label className="field">
                    Название
                    <input
                        autoFocus
                        value={name}
                        maxLength={40}
                        placeholder="Например, Сломался лифт"
                        onChange={(e) => setName(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && ok) onSave(name)
                        }}
                    />
                </label>

                <div className="sheet-actions">
                    <button onClick={onClose}>Отмена</button>
                    <button className="btn-primary" disabled={!ok} onClick={() => onSave(name)}>
                        Добавить
                    </button>
                </div>
            </div>
        </div>
    )
}

const tabsList = [
    ['home', 'Главная'],
    ['devices', 'Устройства'],
    ['scenarios', 'Сценарии'],
]

export default function App() {
    const [tab, setTab] = useState('home')
    const [devices, setDevices] = useState(() => initialDevices.map(upgradeDevice))
    const [scenarios, setScenarios] = useState(initialScenarios)
    const [customSituations, setCustomSituations] = useState([])
    const [emergencies, setEmergencies] = useState([])
    const [tickets, setTickets] = useState([])
    const [activeId, setActiveId] = useState(null)
    const [dockOpen, setDockOpen] = useState(false)
    const [dockKind, setDockKind] = useState('devices')
    const [sheet, setSheet] = useState(null)
    const [newSitOpen, setNewSitOpen] = useState(false)
    const [addDevOpen, setAddDevOpen] = useState(false)
    const [editDevId, setEditDevId] = useState(null)

    const sits = [...situations, ...customSituations]

    const sensors = useSensors(
        useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
        useSensor(TouchSensor, { activationConstraint: { delay: 180, tolerance: 8 } }),
    )

    const toggleDevice = (id) =>
        setDevices((ds) => ds.map((d) => (d.id === id ? { ...d, on: !d.on } : d)))

    const addDevice = (data) => {
        setDevices((ds) => [...ds, { id: uid('d'), on: false, ...data }])
        setAddDevOpen(false)
    }

    const saveDeviceParams = (id, params) => {
        setDevices((ds) => ds.map((d) => (d.id === id ? { ...d, params } : d)))
        setEditDevId(null)
    }

    const removeDevice = (id) => {
        setDevices((ds) => ds.filter((d) => d.id !== id))
        setScenarios((ss) =>
            ss.map((s) => ({ ...s, blocks: normalizeBlocks(s.blocks.filter((b) => b.deviceId !== id)) })),
        )
    }

    const addScenario = () =>
        setScenarios((ss) => [
            ...ss,
            { id: uid('s'), title: `Сценарий ${ss.length + 1}`, blocks: [], conditions: [] },
        ])

    const renameScenario = (id, title) =>
        setScenarios((ss) => ss.map((s) => (s.id === id ? { ...s, title } : s)))

    const removeScenario = (id) => setScenarios((ss) => ss.filter((s) => s.id !== id))

    const removeBlock = (blockId) =>
        setScenarios((ss) =>
            ss.map((s) => ({ ...s, blocks: normalizeBlocks(s.blocks.filter((b) => b.id !== blockId)) })),
        )

    const addCustomSituation = (label) => {
        const clean = label.trim()
        const found = sits.find((s) => s.label.toLowerCase() === clean.toLowerCase())
        if (found) return found
        const s = { type: uid('custom_'), label: clean }
        setCustomSituations((cs) => [...cs, s])
        return s
    }

    const startEmergency = ({ type, name, amount, unit }) => {
        const sit = type === '__custom' ? addCustomSituation(name) : situationOf(type, sits)
        if (!sit) return
        setEmergencies((es) => [
            ...es,
            { id: uid('e'), type: sit.type, label: sit.label, amount, unit },
        ])

        const auto = scenarios.filter((s) =>
            (s.conditions ?? []).some((c) => c.type === sit.type && c.action === 'support'),
        )
        if (auto.length > 0)
            setTickets((ts) => [
                ...auto.map((s) => ({
                    id: uid('t'),
                    subject: sit.label,
                    text: `Сценарий «${s.title}»`,
                    deviceId: null,
                    done: false,
                    auto: true,
                })),
                ...ts,
            ])
    }

    const addTicket = (data) =>
        setTickets((ts) => [{ id: uid('t'), done: false, auto: false, ...data }, ...ts])

    const closeTicket = (id) =>
        setTickets((ts) => ts.map((t) => (t.id === id ? { ...t, done: true } : t)))

    const endEmergency = (id) => setEmergencies((es) => es.filter((e) => e.id !== id))

    const openAddCond = (scenarioId) => setSheet({ mode: 'add', scenarioId })
    const openEditCond = (scenarioId, condId) => setSheet({ mode: 'edit', scenarioId, condId })

    const saveCond = ({ newLabel, ...data }) => {
        const { mode, scenarioId, condId } = sheet
        const finalType = newLabel ? addCustomSituation(newLabel).type : data.type
        const payload = { ...data, type: finalType }
        const newId = uid('c')
        setScenarios((ss) =>
            ss.map((s) => {
                if (s.id !== scenarioId) return s
                const list = s.conditions ?? []
                if (mode === 'add') return { ...s, conditions: [...list, { id: newId, ...payload }] }
                return { ...s, conditions: list.map((c) => (c.id === condId ? { ...c, ...payload } : c)) }
            }),
        )
        setSheet(null)
    }

    const removeCond = (scenarioId, condId) =>
        setScenarios((ss) =>
            ss.map((s) =>
                s.id === scenarioId
                    ? { ...s, conditions: (s.conditions ?? []).filter((c) => c.id !== condId) }
                    : s,
            ),
        )

    const deleteCond = () => {
        removeCond(sheet.scenarioId, sheet.condId)
        setSheet(null)
    }

    const saveNewSituation = (label) => {
        addCustomSituation(label)
        setNewSitOpen(false)
        setDockKind('situations')
    }

    const handleDragEnd = ({ active, over }) => {
        setActiveId(null)
        if (!over || active.id === over.id) return
        const [aType, aId] = split(active.id)
        const oParts = split(over.id)
        const [oType, oId] = oParts

        const scenarioIdOf = (list) =>
            oType === 'block' ? scenarioOfBlock(list, oId)?.id : oId

        if (aType === 'cond') {
            const target = scenarios.find((s) => s.id === scenarioIdOf(scenarios))
            const sit = situationOf(aId, sits)
            if (!target || !sit) return
            const nc = {
                id: uid('c'),
                type: aId,
                time: '',
                value: sit.value ?? '',
                action: 'off',
                actionText: '',
            }
            setScenarios((prev) =>
                prev.map((s) =>
                    s.id === target.id ? { ...s, conditions: [...(s.conditions ?? []), nc] } : s,
                ),
            )
            setSheet({ mode: 'edit', scenarioId: target.id, condId: nc.id })
            return
        }

        setScenarios((prev) => {
            const target = prev.find((s) => s.id === scenarioIdOf(prev))
            if (!target) return prev

            if (aType === 'scenario') {
                const from = prev.findIndex((s) => s.id === aId)
                const to = prev.findIndex((s) => s.id === target.id)
                return arrayMove(prev, from, to)
            }

            let moved
            let src = null
            if (aType === 'device') {
                moved = { id: uid('b'), deviceId: aId }
            } else if (aType === 'block') {
                src = scenarioOfBlock(prev, aId)
                moved = src?.blocks.find((b) => b.id === aId)
                if (!moved) return prev
            } else {
                return prev
            }

            const tCols = columnsOf(target.blocks).map((c) => [...c])
            const sCols = src && src.id !== target.id ? columnsOf(src.blocks).map((c) => [...c]) : tCols

            let place
            if (oType === 'block') {
                const col = tCols.find((c) => c.some((b) => b.id === oId))
                if (!col) return prev
                const ti = col.findIndex((b) => b.id === oId)
                const mi = col.findIndex((b) => b.id === aId)
                const above = mi > ti
                place = () => {
                    const i = col.findIndex((b) => b.id === oId)
                    col.splice(above ? i : i + 1, 0, moved)
                }
            } else if (oType === 'col') {
                const col = tCols[Number(oParts[2])]
                if (!col) return prev
                place = () => col.push(moved)
            } else if (oType === 'gap') {
                const ref = tCols[Number(oParts[2])]
                place = () => tCols.splice(ref ? tCols.indexOf(ref) : tCols.length, 0, [moved])
            } else {
                place = () => tCols.push([moved])
            }

            if (src) {
                const from = sCols.find((c) => c.some((b) => b.id === aId))
                from.splice(
                    from.findIndex((b) => b.id === aId),
                    1,
                )
            }
            place()

            const clean = (cols) => fromColumns(cols.filter((c) => c.length))
            return prev.map((s) => {
                if (s.id === target.id) return { ...s, blocks: clean(tCols) }
                if (src && s.id === src.id) return { ...s, blocks: clean(sCols) }
                return s
            })
        })
    }

    let overlay = null
    if (activeId) {
        const [t, id] = split(activeId)
        if (t === 'device') {
            overlay = <div className="chip lifted">{devices.find((d) => d.id === id)?.name}</div>
        } else if (t === 'cond') {
            overlay = <div className="chip lifted">{situationOf(id, sits)?.label}</div>
        } else if (t === 'block') {
            const b = scenarioOfBlock(scenarios, id)?.blocks.find((x) => x.id === id)
            overlay = (
                <div className="block lifted">{devices.find((d) => d.id === b?.deviceId)?.name}</div>
            )
        } else if (t === 'scenario') {
            overlay = (
                <div className="card scenario lifted overlay-title">
                    {scenarios.find((s) => s.id === id)?.title}
                </div>
            )
        }
    }

    const editDev = devices.find((d) => d.id === editDevId)
    const onCount = devices.filter((d) => d.on).length
    const dockDevices = dockKind === 'devices'

    const titles = {
        home: ['Добро пожаловать', 'Ваша квартира'],
        devices: ['Устройства', `Включено ${onCount} из ${devices.length}`],
        scenarios: ['Сценарии', `Всего сценариев: ${scenarios.length}`],
    }
    const [title, subtitle] = titles[tab]

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={collide}
            onDragStart={({ active }) => setActiveId(active.id)}
            onDragCancel={() => setActiveId(null)}
            onDragEnd={handleDragEnd}
        >
            <div className="phone">
                <header className="top">
                    <h1>{title}</h1>
                    <p className="sub">{subtitle}</p>
                </header>

                <main className="content">
                    {tab === 'home' && (
                        <HomePage
                            devices={devices}
                            scenarios={scenarios}
                            emergencies={emergencies}
                            sits={sits}
                            tickets={tickets}
                            onStart={startEmergency}
                            onEnd={endEmergency}
                            onTicket={addTicket}
                            onCloseTicket={closeTicket}
                        />
                    )}

                    {tab === 'devices' && (
                        <DevicesPage
                            devices={devices}
                            onToggle={toggleDevice}
                            onRemove={removeDevice}
                            onAdd={() => setAddDevOpen(true)}
                            onEdit={setEditDevId}
                        />
                    )}

                    {tab === 'scenarios' && (
                        <ScenariosPage
                            scenarios={scenarios}
                            devices={devices}
                            sits={sits}
                            onRename={renameScenario}
                            onRemoveBlock={removeBlock}
                            onRemove={removeScenario}
                            onAdd={addScenario}
                            onAddCond={openAddCond}
                            onEditCond={openEditCond}
                            onRemoveCond={removeCond}
                            onEditDevice={setEditDevId}
                        />
                    )}
                </main>

                {tab === 'scenarios' && (
                    <div className="dock">
                        <div className="dock-tabs">
                            <button
                                className={dockDevices ? 'active' : ''}
                                onClick={() => setDockKind('devices')}
                            >
                                Устройства
                            </button>
                            <button
                                className={!dockDevices ? 'active' : ''}
                                onClick={() => setDockKind('situations')}
                            >
                                Ситуации
                            </button>
                        </div>

                        <button
                            className="dock-toggle"
                            onClick={() => setDockOpen((o) => !o)}
                            aria-expanded={dockOpen}
                        >
                            <span>
                                {dockDevices
                                    ? `Все устройства (${devices.length})`
                                    : `Все ситуации (${sits.length})`}
                            </span>
                            <span className="caret">{dockOpen ? '▾' : '▴'}</span>
                        </button>

                        {!dockDevices && (
                            <button className="dock-custom" onClick={() => setNewSitOpen(true)}>
                                Создать свою ситуацию +
                            </button>
                        )}

                        <div className="dock-title">
                            {dockDevices
                                ? 'Зажмите устройство и перетащи в сценарий'
                                : 'Зажмите ситуацию и перетащи в сценарий'}
                        </div>

                        <div className={dockOpen ? 'dock-menu' : 'dock-list'}>
                            {dockDevices ? (
                                <>
                                    {devices.map((d) => (
                                        <DockChip key={d.id} device={d} wide={dockOpen} />
                                    ))}
                                    {devices.length === 0 && (
                                        <span className="hint">Сначала добавь устройства</span>
                                    )}
                                </>
                            ) : (
                                sits.map((s) => <SituationChip key={s.type} situation={s} wide={dockOpen} />)
                            )}
                        </div>
                    </div>
                )}

                <nav className="tabs">
                    {tabsList.map(([key, label]) => (
                        <button
                            key={key}
                            className={tab === key ? 'active' : ''}
                            onClick={() => setTab(key)}
                        >
                            {label}
                        </button>
                    ))}
                </nav>
            </div>

            {sheet && (
                <ConditionSheet
                    key={`${sheet.mode}-${sheet.scenarioId}-${sheet.condId ?? 'new'}`}
                    sheet={sheet}
                    scenarios={scenarios}
                    sits={sits}
                    onSave={saveCond}
                    onDelete={deleteCond}
                    onClose={() => setSheet(null)}
                />
            )}

            {editDev && (
                <DeviceSheet
                    key={editDev.id}
                    device={editDev}
                    onSave={saveDeviceParams}
                    onClose={() => setEditDevId(null)}
                />
            )}

            {addDevOpen && <AddDeviceSheet onSave={addDevice} onClose={() => setAddDevOpen(false)} />}

            {newSitOpen && (
                <NewSituationSheet onSave={saveNewSituation} onClose={() => setNewSitOpen(false)} />
            )}

            <DragOverlay>{overlay}</DragOverlay>
        </DndContext>
    )
}
