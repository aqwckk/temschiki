import { useEffect, useRef } from 'react'

const RECONNECT_DELAY = 2000

// Подписка на события бэкенда по WebSocket с переподключением при обрыве
export function useLive(onEvent) {
    const handlerRef = useRef(onEvent)
    handlerRef.current = onEvent

    useEffect(() => {
        let socket = null
        let retry = null
        let stopped = false

        const connect = () => {
            let protocol = 'ws'
            if (window.location.protocol === 'https:') {
                protocol = 'wss'
            }
            socket = new WebSocket(`${protocol}://${window.location.host}/ws`)
            socket.onmessage = (message) => handlerRef.current(JSON.parse(message.data))
            socket.onclose = () => {
                if (!stopped) {
                    retry = setTimeout(connect, RECONNECT_DELAY)
                }
            }
        }

        connect()
        return () => {
            stopped = true
            clearTimeout(retry)
            socket.close()
        }
    }, [])
}
