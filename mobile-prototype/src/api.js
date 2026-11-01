// Запросы к бэкенду. Пути относительные: в разработке их проксирует vite, в сборке nginx.
// id приходят числами, а фронт сравнивает их со строками из dnd ("device:5"),
// поэтому на входе приводим id к строкам, а на выходе обратно к числам.

// типы устройств нужны, чтобы превратить сигналы устройства в параметры карточки
let deviceTypes = []

async function request(method, path, body) {
    const options = { method, headers: {} }
    if (body !== undefined) {
        options.headers['Content-Type'] = 'application/json'
        options.body = JSON.stringify(body)
    }
    const response = await fetch(`/api${path}`, options)
    if (!response.ok) {
        const text = await response.text()
        throw new Error(`${method} ${path}: ${response.status} ${text}`)
    }
    if (response.status === 204) {
        return null
    }
    return response.json()
}

// control сигнала бэкенда -> тип параметра фронта, остальное считаем числом
const PARAM_TYPES = { switch: 'switch', list: 'list', text: 'text' }

function paramType(signal) {
    if (signal.control === 'text' && typeof signal.default === 'string' && signal.default.startsWith('#')) {
        return 'color'
    }
    return PARAM_TYPES[signal.control] ?? 'counter'
}

function paramAccess(signal) {
    if (signal.management === 'r') {
        return 'r'
    }
    return 'rw'
}

function toParam(signal, values) {
    let value = values[signal.name]
    if (value === undefined) {
        value = signal.default ?? 0
    }
    return {
        id: signal.name,
        label: signal.title,
        type: paramType(signal),
        access: paramAccess(signal),
        value,
        unit: signal.measure || undefined,
        min: signal.min ?? undefined,
        max: signal.max ?? undefined,
        layout: signal.layout ?? undefined,
    }
}

function fromDevice(device) {
    const type = deviceTypes.find((t) => t.family === device.family)
    let params = []
    let ujin = false
    if (type) {
        // прошивку и прочую служебную обвязку жителю не показываем
        params = type.signals.filter((s) => s.kind !== 'system').map((s) => toParam(s, device.values ?? {}))
        ujin = type.builtin
    }
    return { ...device, id: String(device.id), params, ujin }
}

function fromBlock(block) {
    if (block.kind !== 'device') {
        return block
    }
    return { ...block, deviceId: String(block.deviceId) }
}

function fromScenario(scenario) {
    return { ...scenario, id: String(scenario.id), blocks: scenario.blocks.map(fromBlock) }
}

function toBlock(block) {
    if (block.kind && block.kind !== 'device') {
        return block
    }
    return {
        id: block.id,
        kind: 'device',
        deviceId: Number(block.deviceId),
        on: block.on ?? true,
        col: block.col ?? null,
    }
}

function toScenario(scenario) {
    return {
        title: scenario.title,
        enabled: scenario.enabled ?? true,
        blocks: scenario.blocks.map(toBlock),
        conditions: scenario.conditions ?? [],
    }
}

// параметр из конструктора фронта -> сигнал декларации бэкенда
const SIGNAL_CONTROLS = { switch: 'switch', counter: 'counter', list: 'list', text: 'text', color: 'text' }

function toSignal(param, index) {
    let kind = 'capability'
    if (param.type === 'text' || param.type === 'color') {
        kind = 'property'
    }
    return {
        name: `p${index + 1}`,
        title: param.label,
        kind,
        control: SIGNAL_CONTROLS[param.type] ?? 'text',
        measure: param.unit ?? '',
        min: param.min ?? null,
        max: param.max ?? null,
        default: param.value ?? 0,
        layout: param.layout ?? null,
    }
}

export function fromEmergency(emergency) {
    return { ...emergency, id: String(emergency.id) }
}

export async function getDeviceTypes() {
    deviceTypes = await request('GET', '/device-types')
    return deviceTypes
}

export async function getDevices() {
    const devices = await request('GET', '/devices')
    return devices.map(fromDevice)
}

export async function getDevice(id) {
    return fromDevice(await request('GET', `/devices/${id}`))
}

export async function createDevice(name, family) {
    return fromDevice(await request('POST', '/devices', { name, family }))
}

// свое устройство: сначала тип в конструкторе, потом устройство этого типа
export async function createCustomDevice(name, params) {
    const family = `c${Date.now().toString(36)}`
    const type = await request('POST', '/device-types', {
        family,
        title: name,
        signals: params.map(toSignal),
    })
    deviceTypes = [...deviceTypes, type]
    return createDevice(name, family)
}

export async function toggleDevice(id) {
    return fromDevice(await request('POST', `/devices/${id}/toggle`, {}))
}

export function sendCommand(id, signal, value) {
    return request('POST', `/devices/${id}/command`, { signal, value })
}

export function deleteDevice(id) {
    return request('DELETE', `/devices/${id}`)
}

export async function getScenarios() {
    const scenarios = await request('GET', '/scenarios')
    return scenarios.map(fromScenario)
}

export async function createScenario(title) {
    return fromScenario(await request('POST', '/scenarios', { title }))
}

export function saveScenario(scenario) {
    return request('PUT', `/scenarios/${scenario.id}`, toScenario(scenario))
}

export function deleteScenario(id) {
    return request('DELETE', `/scenarios/${id}`)
}

export function reorderScenarios(ids) {
    return request('PUT', '/scenarios/order', { ids: ids.map(Number) })
}

export function getSituations() {
    return request('GET', '/situations')
}

export function createSituation(label) {
    return request('POST', '/situations', { label })
}

export async function getEmergencies() {
    const emergencies = await request('GET', '/emergencies')
    return emergencies.map(fromEmergency)
}

export async function startEmergency({ type, name, amount, unit }) {
    return fromEmergency(await request('POST', '/emergencies', { type, name, amount, unit }))
}

export function endEmergency(id) {
    return request('DELETE', `/emergencies/${id}`)
}

