import React from 'react';

export const SCORPYO_URL = 'ws://127.0.0.1:13254';

export function useScorpyo() {

    const [data, setData] = React.useState();

    const scorpyo = React.useMemo(() => {
        let url = SCORPYO_URL;
        const scorpyo = new ScorpyoClient(url, {
            onData: (data) => {
                setData(data);
            }
        })
        return scorpyo;
    }, []);

    const close = React.useCallback(() => {
        if (scorpyo) {
            scorpyo.close();
        }
    }, [scorpyo]);

    const subscribe = React.useCallback(() => {
        if (scorpyo) {
            scorpyo.subscribe();
        }
    }, [scorpyo]);

    return {data, subscribe, close};
}

export default function ScorpyoClient(url, listener) {

    let ws = null;
    const pendingCommands = [];

    const assureOpen = async (command) => {
        if (ws) {
            return;
        }

        if (command) {
            pendingCommands.push(command);
        }

        ws = new WebSocket(url);

        ws.onopen = () => {
            let pendingCommand = pendingCommands.pop();
            while (pendingCommand != null) {
                ws.send(JSON.stringify(pendingCommand));
                pendingCommand = pendingCommands.shift();
            }
        }

        ws.onclose = (closeEvent) => {
            console.log("Scorpyo connection closed, code=" + closeEvent.code);
        }

        ws.onmessage = (ev) => {
            const message = JSON.parse(ev.data);
            listener.onData(message)
            console.log(message);
        }
    }

    const subscribe = (params) => {
        assureOpen(Object.assign({command: 'subscribe'}, params));
    }

    const close = () => {
        if (ws) {
            ws.close();
        }
    }

    const send = (command) => {
        if (ws) {
            ws.send(JSON.stringify(command));
        }
        else {
            pendingCommands.push(command);
        }
    }

    return {subscribe, close, send};
}