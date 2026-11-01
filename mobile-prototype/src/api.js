// Запросы к бэкенду. Пути относительные: в разработке их проксирует vite, в сборке nginx.
// id приходят числами, а фронт сравнивает их со строками из dnd ("device:5"),
// поэтому на входе приводим id к строкам, а на выходе обратно к числам.

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

function fromDevice(device) {
    return { ...device, id: String(device.id) }
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
    return { id: block.id, kind: 'device', deviceId: Number(block.deviceId), on: block.on ?? true }
}

function toScenario(scenario) {
    return {
        title: scenario.title,
        enabled: scenario.enabled ?? true,
        blocks: scenario.blocks.map(toBlock),
        conditions: scenario.conditions ?? [],
    }
}

export function fromEmergency(emergency) {
    return { ...emergency, id: String(emergency.id) }
}

export async function getDevices() {
    const devices = await request('GET', '/devices')
    return devices.map(fromDevice)
}

export function getDeviceTypes() {
    return request('GET', '/device-types')
}

export async function createDevice(name, family) {
    return fromDevice(await request('POST', '/devices', { name, family }))
}

export async function toggleDevice(id) {
    return fromDevice(await request('POST', `/devices/${id}/toggle`, {}))
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
