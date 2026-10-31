import { useRef, useState } from 'react'
import {
    DndContext,
    DragOverlay,
    MouseSensor,
    TouchSensor,
    closestCenter,
    useDraggable,
    useSensor,
    useSensors,
} from '@dnd-kit/core'
import {
    SortableContext,
    arrayMove,
    rectSortingStrategy,
    useSortable,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { deviceTemplates, initialDevices, initialScenarios } from './mock'

let counter = 100
const uid = (p) => `${p}${counter++}`
const split = (id) => String(id).split(':')
const scenarioOfBlock = (list, blockId) =>
    list.find((s) => s.blocks.some((b) => b.id === blockId))

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

function HomePage({ devices, scenarios, emergencies, sits, onStart, onEnd }) {
    const options = sits.filter((s) => !s.unit && s.type !== 'night')
    const [type, setType] = useState(options[0]?.type ?? '__custom')
    const [name, setName] = useState('')
    const [amount, setAmount] = useState(2)
    const [unit, setUnit] = useState('d')

    const custom = type === '__custom'
    const canStart = Number(amount) >= 1 && (!custom || name.trim().length > 0)
    const onCount = devices.filter((d) => d.on).length
    const affected = (e) =>
        scenarios.filter((s) => (s.conditions ?? []).some((c) => c.type === e.type))
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
                                        ? `Затронуты сценарии: ${list.map((s) => s.title).join(', ')}`
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
        </>
    )
}

function DeviceCard({ device, onToggle, onRemove }) {
    return (
        <article className={`card device ${device.on ? 'is-on' : ''}`}>
            <div className="device-top">
                <span className="device-state">{device.on ? 'Включено' : 'Выключено'}</span>
                <button
                    className="toggle"
                    role="switch"
                    aria-checked={device.on}
                    aria-label={`Переключить ${device.name}`}
                    onClick={() => onToggle(device.id)}
                >
                    <span className="knob" />
                </button>
            </div>

            <h2 className="device-name">{device.name}</h2>

            <ul className="params">
                {device.params.map((p) => (
                    <li key={p}>{p}</li>
                ))}
            </ul>

            <button className="link" onClick={() => onRemove(device.id)}>
                Удалить
            </button>
        </article>
    )
}

function DevicesPage({ devices, onToggle, onRemove, onAdd }) {
    return (
        <>
            {devices.length === 0 && <p className="empty">Устройств пока нет</p>}
            <div className="device-list">
                {devices.map((d) => (
                    <DeviceCard key={d.id} device={d} onToggle={onToggle} onRemove={onRemove} />
                ))}
            </div>
            <button className="card add" onClick={onAdd}>
                Добавить новое устройство +
            </button>
        </>
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

function Block({ block, device, onRemove }) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
        useSortable({ id: `block:${block.id}` })
    return (
        <div
            ref={setNodeRef}
            className={`block ${isDragging ? 'ghost' : ''}`}
            style={{ transform: CSS.Transform.toString(transform), transition }}
            {...attributes}
            {...listeners}
        >
            <span className={`dot ${device?.on ? 'on' : ''}`} />
            <span>{device?.name ?? '?'}</span>
            <button className="x" onClick={() => onRemove(block.id)} aria-label="Убрать из сценария">
                ×
            </button>
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
}) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
        useSortable({ id: `scenario:${scenario.id}` })
    const inputRef = useRef(null)
    const conditions = scenario.conditions ?? []
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

            <div className="blocks">
                <SortableContext
                    items={scenario.blocks.map((b) => `block:${b.id}`)}
                    strategy={rectSortingStrategy}
                >
                    {scenario.blocks.map((b) => (
                        <Block
                            key={b.id}
                            block={b}
                            device={devices.find((d) => d.id === b.deviceId)}
                            onRemove={onRemoveBlock}
                        />
                    ))}
                </SortableContext>
                {scenario.blocks.length === 0 && (
                    <span className="hint">Необходимо перенести устройство из панели внизу</span>
                )}
            </div>

            <div className="conds">
                <div className="conds-title">Ситуации, влияющие на сценарий</div>
                <div className="conds-list">
                    {conditions.map((c) => (
                        <div key={c.id} className="cond-wrap">
                            <button className="cond" onClick={() => onEditCond(scenario.id, c.id)}>
                                {condText(c, sits)}
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

    const isNew = type === '__new'
    const sit = situationOf(type, sits)
    const canSave = !isNew || newName.trim().length > 0

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
    const [devices, setDevices] = useState(initialDevices)
    const [scenarios, setScenarios] = useState(initialScenarios)
    const [customSituations, setCustomSituations] = useState([])
    const [emergencies, setEmergencies] = useState([])
    const [activeId, setActiveId] = useState(null)
    const [dockOpen, setDockOpen] = useState(false)
    const [dockKind, setDockKind] = useState('devices')
    const [sheet, setSheet] = useState(null)
    const [newSitOpen, setNewSitOpen] = useState(false)

    const sits = [...situations, ...customSituations]

    const sensors = useSensors(
        useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
        useSensor(TouchSensor, { activationConstraint: { delay: 180, tolerance: 8 } }),
    )

    const toggleDevice = (id) =>
        setDevices((ds) => ds.map((d) => (d.id === id ? { ...d, on: !d.on } : d)))

    const addDevice = () => {
        const t = deviceTemplates[devices.length % deviceTemplates.length]
        setDevices((ds) => [...ds, { id: uid('d'), on: false, ...t }])
    }

    const removeDevice = (id) => {
        setDevices((ds) => ds.filter((d) => d.id !== id))
        setScenarios((ss) =>
            ss.map((s) => ({ ...s, blocks: s.blocks.filter((b) => b.deviceId !== id) })),
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
            ss.map((s) => ({ ...s, blocks: s.blocks.filter((b) => b.id !== blockId) })),
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
    }

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
        const [oType, oId] = split(over.id)

        if (aType === 'cond') {
            const target =
                oType === 'scenario'
                    ? scenarios.find((s) => s.id === oId)
                    : scenarioOfBlock(scenarios, oId)
            const sit = situationOf(aId, sits)
            if (!target || !sit) return
            const nc = { id: uid('c'), type: aId, time: '', value: sit.value ?? '' }
            setScenarios((prev) =>
                prev.map((s) =>
                    s.id === target.id ? { ...s, conditions: [...(s.conditions ?? []), nc] } : s,
                ),
            )
            setSheet({ mode: 'edit', scenarioId: target.id, condId: nc.id })
            return
        }

        setScenarios((prev) => {
            const target =
                oType === 'scenario' ? prev.find((s) => s.id === oId) : scenarioOfBlock(prev, oId)
            if (!target) return prev

            if (aType === 'scenario') {
                const from = prev.findIndex((s) => s.id === aId)
                const to = prev.findIndex((s) => s.id === target.id)
                return arrayMove(prev, from, to)
            }

            const insertAt =
                oType === 'block' ? target.blocks.findIndex((b) => b.id === oId) : target.blocks.length

            if (aType === 'device') {
                const nb = { id: uid('b'), deviceId: aId }
                return prev.map((s) =>
                    s.id === target.id
                        ? { ...s, blocks: [...s.blocks.slice(0, insertAt), nb, ...s.blocks.slice(insertAt)] }
                        : s,
                )
            }

            if (aType === 'block') {
                const src = scenarioOfBlock(prev, aId)
                if (!src) return prev
                if (src.id === target.id) {
                    const from = src.blocks.findIndex((b) => b.id === aId)
                    const to = oType === 'block' ? insertAt : src.blocks.length - 1
                    return prev.map((s) =>
                        s.id === src.id ? { ...s, blocks: arrayMove(s.blocks, from, to) } : s,
                    )
                }
                const moved = src.blocks.find((b) => b.id === aId)
                return prev.map((s) => {
                    if (s.id === src.id) return { ...s, blocks: s.blocks.filter((b) => b.id !== aId) }
                    if (s.id === target.id)
                        return {
                            ...s,
                            blocks: [...s.blocks.slice(0, insertAt), moved, ...s.blocks.slice(insertAt)],
                        }
                    return s
                })
            }
            return prev
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
            collisionDetection={closestCenter}
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
                            onStart={startEmergency}
                            onEnd={endEmergency}
                        />
                    )}

                    {tab === 'devices' && (
                        <DevicesPage
                            devices={devices}
                            onToggle={toggleDevice}
                            onRemove={removeDevice}
                            onAdd={addDevice}
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

            {newSitOpen && (
                <NewSituationSheet onSave={saveNewSituation} onClose={() => setNewSitOpen(false)} />
            )}

            <DragOverlay>{overlay}</DragOverlay>
        </DndContext>
    )
}
