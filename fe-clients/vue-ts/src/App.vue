<template>
  <div>
    <a href="https://vitejs.dev" target="_blank">
      <img src="/vite.svg" class="logo" alt="Vite logo" />
    </a>
    <a href="https://vuejs.org/" target="_blank">
      <img src="./assets/vue.svg" class="logo vue" alt="Vue logo" />
    </a>
    <h2>Talk To Your Database (Prototype)</h2>
    <h3>Framework: Vue-TS</h3>

    <input
      type="text"
      v-model="prompt"
      placeholder="Enter your prompt"
      @keyup.enter="sendPrompt"
    />

    <section v-for="(result, index) in promptResults" :key="index">
      <h3>{{ result.prompt }}</h3>
      <pre>{{ JSON.stringify(result.results, null, 2) }}</pre>
      <code>{{ result.sql }}</code>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

interface PromptResult {
  prompt: string;
  results: Record<string, any>[];
  sql: string;
}

const prompt = ref("");

// code: load this from local storage or default to empty list
const promptResults = ref<PromptResult[]>(
  JSON.parse(localStorage.getItem("promptResults") || "[]")
);

const sendPrompt = async () => {
  if (prompt.value.trim() === "") return;
  try {
    const response = await fetch("http://localhost:3000/prompt", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt: prompt.value }),
    });
    if (!response.ok) throw new Error("Network response was not ok");
    const data = await response.json();
    data.results = JSON.parse(data.results); // Assuming 'results' is a JSON string that needs to be parsed
    promptResults.value.push(data);
    localStorage.setItem("promptResults", JSON.stringify(promptResults.value));
    // code: save this to local storage
    prompt.value = ""; // Clear the prompt input after submission
  } catch (error) {
    console.error("There was a problem with the fetch operation:", error);
  }
};
</script>

<style scoped>
.logo,
input,
button,
pre,
section,
code {
  background-color: #1e1e1e; /* Dark background */
  color: #ffffff; /* White text */
  border: none;
}

input,
button {
  padding: 0.5em 1em;
  text-align: center;
}

pre {
  overflow: auto;
  max-height: 200px;
}

section {
  display: flex;
  flex-direction: column;
  gap: 1em;
  padding: 1em;
}

/* Existing styles */
.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
</style>
