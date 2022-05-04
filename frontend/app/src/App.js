import React, { useEffect } from 'react';

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
        <p>
          Welcome to Scorpyo!
        </p>
      </header>
    </div>
  );
}

export default App;
