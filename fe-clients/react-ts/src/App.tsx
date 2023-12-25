//  code: add a enter key event that takes the 'prompt' and makes a http post request to localhost:3000/prompt using fetch. Take the json response and push it into the 'promptResults' list. Make sure to json.parse the response.results' it will be a json string.

import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

// Define the PromptResult type
type PromptResult = {
  prompt: string;
  results: Record<string, any>[];
  sql: string;
};

function App() {

  // State variables
    const [prompt, setPrompt] = useState<string>('');
  // Load promptResults from local storage or default to empty list
    const [promptResults, setPromptResults] = useState<PromptResult[]>(
      () => JSON.parse(localStorage.getItem('promptResults') || '[]')
    );

    // Function to handle the Enter key press
    function handleKeyPress(event: React.KeyboardEvent<HTMLInputElement>) {
      if (event.key === 'Enter') {
        handleSubmit();
      }
    }

    // Function to handle the submit action
    function handleSubmit() {
      fetch('http://localhost:3000/prompt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      })
      .then(response => response.json())
      .then(data => {
        const resultsParsed = {
          ...data,
          results: JSON.parse(data.results),
        };
        const newPromptResults = [...promptResults, resultsParsed];
        setPromptResults(newPromptResults);
        localStorage.setItem('promptResults', JSON.stringify(newPromptResults));
      })
      .catch(error => console.error('Error:', error));
    }
    
  return (
    <>
      <div>
        <a href="https://bhuma.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
      </div>
      <h1>Bhuma AI</h1>
      <h2>Chat assistant for viz generation</h2>
      {/* Dark theme input and button */}
      <input
        type="text"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyPress={handleKeyPress}
        className="dark-theme"
      />
      <button onClick={handleSubmit} className="dark-theme">Submit</button>

      
      {/* List of prompt results */}
      <div className="flex-col-gap">
        {promptResults.map((result, index) => {
          return (
            <section key={index} className="dark-theme">
              {/* Display the prompt used */}
              <p>Prompt: {result.prompt}</p>
              <pre>{JSON.stringify(result.results, null, 2)}</pre>
              <code>{result.sql}</code>
            </section>
          );
        })}
      </div>
    </>
  )
}

export default App
