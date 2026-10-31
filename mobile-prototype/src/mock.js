// моки

export const initialDevices = [
  { id: 'd1', name: 'Термостат', params: ['Цель: 22°C', 'Сейчас: 20°C'], on: false },
]

export const deviceTemplates = [
  { name: 'Термостат', params: ['Цель: 22°C', 'Сейчас: 20°C'] },
]

export const initialScenarios = [
  { id: 's1', title: 'Сценарий 1', blocks: [{ id: 'b1', deviceId: 'd1' }] },
]
