import { useState } from 'react'
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
const split = (id) => String(id).split(':') // 'device:d1' -> ['device', 'd1']
const scenarioOfBlock = (list, blockId) =>
    list.find((s) => s.blocks.some((b) => b.id === blockId))

function DeviceCard({ device, onToggle, onRemove }) {
    return (
        <div className="card device">
            <div className="device-top">
                <div className="device-name">{device.name}</div>
                <button
                    className={`switch ${device.on ? 'on' : ''}`}
                    onClick={() => onToggle(device.id)}
                >
                    {device.on ? 'Вкл' : 'Выкл'}
                </button>
            </div>
            <ul className="params">
                {device.params.map((p) => (
                    <li key={p}>{p}</li>
                ))}
            </ul>
            <button className="link" onClick={() => onRemove(device.id)}>
                Удалить
            </button>
        </div>
    )
}

function DockChip({ device }) {
    const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
        id: `device:${device.id}`,
    })
    return (
        <div
            ref={setNodeRef}
            className={`chip ${isDragging ? 'ghost' : ''}`}
            {...attributes}
            {...listeners}
        >
            <span className={`dot ${device.on ? 'on' : ''}`} />
            {device.name}
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
                X
            </button>
        </div>
    )
}

function Scenario({ scenario, devices, onRename, onRemoveBlock, onRemove }) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
        useSortable({ id: `scenario:${scenario.id}` })
    return (
        <section
            ref={setNodeRef}
            className={`card scenario ${isDragging ? 'ghost' : ''}`}
            style={{ transform: CSS.Transform.toString(transform), transition }}
        >
            <header className="scenario-head">
                <button className="handle" {...attributes} {...listeners} aria-label="Переместить сценарий">
                    ⠿
                </button>
                <input
                    value={scenario.title}
                    onChange={(e) => onRename(scenario.id, e.target.value)}
                    aria-label="Название сценария"
                />
                <button className="x" onClick={() => onRemove(scenario.id)} aria-label="Удалить сценарий">
                    X
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
                    <span className="hint">Перетащи сюда устройство из панели внизу</span>
                )}
            </div>
        </section>
    )
}

export default function App() {
    const [tab, setTab] = useState('scenarios')
    const [devices, setDevices] = useState(initialDevices)
    const [scenarios, setScenarios] = useState(initialScenarios)
    const [activeId, setActiveId] = useState(null)

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
        setScenarios((ss) => [...ss, { id: uid('s'), title: `Сценарий ${ss.length + 1}`, blocks: [] }])

    const renameScenario = (id, title) =>
        setScenarios((ss) => ss.map((s) => (s.id === id ? { ...s, title } : s)))

    const removeScenario = (id) => setScenarios((ss) => ss.filter((s) => s.id !== id))

    const removeBlock = (blockId) =>
        setScenarios((ss) =>
            ss.map((s) => ({ ...s, blocks: s.blocks.filter((b) => b.id !== blockId) })),
        )

    const handleDragEnd = ({ active, over }) => {
        setActiveId(null)
        if (!over || active.id === over.id) return
        const [aType, aId] = split(active.id)
        const [oType, oId] = split(over.id)

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

    // что рисовать под пальцем
    let overlay = null
    if (activeId) {
        const [t, id] = split(activeId)
        if (t === 'device') {
            overlay = <div className="chip lifted">{devices.find((d) => d.id === id)?.name}</div>
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
                    <h1>{tab === 'scenarios' ? 'Сценарии' : 'Устройства'}</h1>
                </header>

                <main className="content">
                    {tab === 'scenarios' && (
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
                                        onRename={renameScenario}
                                        onRemoveBlock={removeBlock}
                                        onRemove={removeScenario}
                                    />
                                ))}
                            </SortableContext>
                            <button className="card add" onClick={addScenario}>
                                + Сценарий
                            </button>
                        </>
                    )}

                    {tab !== 'scenarios' && (
                        <>
                            {devices.map((d) => (
                                <DeviceCard key={d.id} device={d} onToggle={toggleDevice} onRemove={removeDevice} />
                            ))}
                            <button className="card add" onClick={addDevice}>
                                + Устройство
                            </button>
                        </>
                    )}
                </main>

                {tab === 'scenarios' && (
                    <div className="dock">
                        <div className="dock-title">Зажми устройство и перетащи в сценарий</div>
                        <div className="dock-list">
                            {devices.map((d) => (
                                <DockChip key={d.id} device={d} />
                            ))}
                            {devices.length === 0 && <span className="hint">Сначала добавь устройства</span>}
                        </div>
                    </div>
                )}

                <nav className="tabs">
                    <button className={tab === 'scenarios' ? 'active' : ''} onClick={() => setTab('scenarios')}>
                        Сценарии
                    </button>
                    <button className={tab === 'devices' ? 'active' : ''} onClick={() => setTab('devices')}>
                        Устройства
                    </button>
                </nav>
            </div>

            <DragOverlay>{overlay}</DragOverlay>
        </DndContext>
    )
}
