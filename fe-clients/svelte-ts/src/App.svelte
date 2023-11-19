<!-- code: add a enter key event that takes the 'prompt' and makes a http post request to localhost:3000/prompt using fetch. Take the json response and push it into the 'promptResults' list. Make sure to json.parse the response.results' it will be a json string.  -->

<script lang="ts">
  import svelteLogo from "./assets/svelte.svg";
  import viteLogo from "/vite.svg";

  let prompt: string = "";
  type PromptResult = {
    prompt: string;
    results: Record<string, any>[];
    sql: string;
  };

  // code: load this from local storage or default to empty list
  let promptResults: PromptResult[] = JSON.parse(localStorage.getItem('promptResults') || '[]');

  async function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "Enter") {
      try {
        const response = await fetch("http://localhost:3000/prompt", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ prompt }),
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        promptResults = [...promptResults, {
          prompt,
          results: JSON.parse(data.results),
          sql: data.sql,
        }];
        localStorage.setItem('promptResults', JSON.stringify(promptResults));
        // code: save promptResults to local storage
        prompt = ""; // Clear the prompt input after submission
      } catch (error) {
        console.error("Error fetching prompt results:", error);
      }
    }
  }
</script>

<main>
  <div>
    <a href="https://vitejs.dev" target="_blank" rel="noreferrer">
      <img src={viteLogo} class="logo" alt="Vite Logo" />
    </a>
    <a href="https://svelte.dev" target="_blank" rel="noreferrer">
      <img src={svelteLogo} class="logo svelte" alt="Svelte Logo" />
    </a>
  </div>
  <h1>Framework: Svelete-TS</h1>
  <h2>TTYDB Prototype</h2>
  <input
    type="text"
    bind:value={prompt}
    placeholder="Enter your prompt"
    on:keydown={handleKeyDown}
  />

  {#each promptResults as result (result.prompt)}
    <section>
      <h3>{result.prompt}</h3>
      <pre>{JSON.stringify(result.results, null, 2)}</pre>
      <code>{result.sql}</code>
    </section>
  {/each}
</main>

<style>
  .logo {
    height: 6em;
    padding: 1.5em;
    will-change: filter;
    transition: filter 300ms;
  }

  input,
  button,
  pre,
  section,
  code {
    background-color: #333;
    color: white;
    border: none;
    padding: 0.5em;
    margin: 0.5em 0;
  }

  input,
  button {
    font-size: 1rem;
  }

  pre,
  code {
    font-family: monospace;
  }
</style>
