import React, { useEffect, useState } from 'react';

import './App.css';
import { useScorpyo } from './useScorpyo';

function App() {

	const {data, subscribe, send} = useScorpyo();

	const [update, setUpdate] = useState();

	useEffect(() => {
		subscribe();
	});

	useEffect(() => {
		if (data !== undefined) {
			setUpdate(data)
		}
	}, [data]);

	return (
		<div className="App">{JSON.stringify(update)}</div>
	);
}

export default App;
