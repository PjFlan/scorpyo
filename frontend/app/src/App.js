import React, { useEffect } from 'react';

import logo from './logo.svg';
import './App.css';

function App() {

    useEffect(() => {
      const ws = new WebSocket('ws://127.0.0.1:13254')
      ws.onmessage = function (event) {
          const json = JSON.parse(event.data);
          try {
              console.log(json);
          } catch (err) {
              console.log(err);
          }
      };
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
      </header>
    </div>
  );
}

export default App;
