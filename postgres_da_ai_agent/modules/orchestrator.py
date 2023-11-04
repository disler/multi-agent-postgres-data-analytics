import dataclasses
import json
from typing import List, Optional, Tuple
import autogen
from postgres_da_ai_agent.agents.instruments import AgentInstruments
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.types import Chat, ConversationResult


class Orchestrator:
    def __init__(
        self,
        name: str,
        agents: List[autogen.ConversableAgent],
        instruments: AgentInstruments,
        validate_results_func: callable = None,
    ):
        self.name = name
        self.agents = agents
        self.messages = []
        self.complete_keyword = "APPROVED"
        self.error_keyword = "ERROR"
        self.instruments = instruments
        self.chats: List[Chat] = []
        self.validate_results_func: callable = validate_results_func

        if len(self.agents) < 2:
            raise Exception("Orchestrator needs at least two agents")

    @property
    def total_agents(self):
        return len(self.agents)

    @property
    def last_message_is_dict(self):
        return isinstance(self.messages[-1], dict)

    @property
    def last_message_is_string(self):
        return isinstance(self.messages[-1], str)

    @property
    def last_message_is_func_call(self):
        return self.last_message_is_dict and self.latest_message.get(
            "function_call", None
        )

    @property
    def last_message_is_content(self):
        return self.last_message_is_dict and self.latest_message.get("content", None)

    @property
    def latest_message(self) -> Optional[str]:
        if not self.messages:
            return None
        return self.messages[-1]

    @property
    def last_message_always_string(self):
        if not self.messages:
            return ""
        if self.last_message_is_content:
            return self.latest_message.get("content", "")
        return str(self.messages[-1])

    def send_message(
        self,
        from_agent: autogen.ConversableAgent,
        to_agent: autogen.ConversableAgent,
        message: str,
    ):
        from_agent.send(message, to_agent)

        self.chats.append(
            Chat(
                from_name=from_agent.name,
                to_name=to_agent.name,
                message=str(message),
            )
        )

    def get_message_as_str(self):
        messages_as_str = ""

        for message in self.messages:
            if message is None:
                continue

            if isinstance(message, dict):
                content_from_dict = message.get("content", None)
                func_call_from_dict = message.get("function_call", None)
                content = content_from_dict or func_call_from_dict
                if not content:
                    continue
                messages_as_str += str(content)
            else:
                messages_as_str += str(message)

        return messages_as_str

    def get_cost_and_tokens(self):
        return llm.estimate_price_and_tokens(self.get_message_as_str())

    def add_message(self, message: str):
        self.messages.append(message)

    def has_functions(self, agent: autogen.ConversableAgent):
        return len(agent._function_map) > 0

    def basic_chat(
        self,
        agent_a: autogen.ConversableAgent,
        agent_b: autogen.ConversableAgent,
        message: str,
    ):
        print(f"basic_chat(): {agent_a.name} -> {agent_b.name}")

        self.send_message(agent_a, agent_b, message)

        reply = agent_b.generate_reply(sender=agent_a)

        self.add_message(reply)

        print(f"basic_chat(): replied with:", reply)

    def memory_chat(
        self,
        agent_a: autogen.ConversableAgent,
        agent_b: autogen.ConversableAgent,
        message: str,
    ):
        print(f"memory_chat() '{agent_a.name}' --> '{agent_b.name}'")

        self.send_message(agent_a, agent_b, message)

        reply = agent_b.generate_reply(sender=agent_a)

        self.send_message(agent_b, agent_b, message)

        self.add_message(reply)

    def function_chat(
        self,
        agent_a: autogen.ConversableAgent,
        agent_b: autogen.ConversableAgent,
        message: str,
    ):
        print(f"function_call(): {agent_a.name} -> {agent_b.name}")

        self.basic_chat(agent_a, agent_a, message)

        assert self.last_message_is_content

        self.basic_chat(agent_a, agent_b, self.latest_message)

    def self_function_chat(self, agent: autogen.ConversableAgent, message: str):
        print(f"self_function_chat(): {agent.name} -> {agent.name}")

        self.send_message(agent, agent, message)

        reply = agent.generate_reply(sender=agent)

        self.send_message(agent, agent, message)

        self.add_message(reply)

        print(f"self_function_chat(): replied with:", reply)

    def spy_on_agents(self, append_to_file: bool = True):
        conversations = []

        for chat in self.chats:
            conversations.append(dataclasses.asdict(chat))

        if append_to_file:
            file_name = self.instruments.agent_chat_file
            with open(file_name, "w") as f:
                f.write(json.dumps(conversations, indent=4))

    def sequential_conversation(self, prompt: str) -> ConversationResult:
        """
        Runs a sequential conversation between agents

        For example
            "Agent A" -> "Agent B" -> "Agent C" -> "Agent D" -> "Agent E"
        """

        print(f"\n\n--------- {self.name} Orchestrator Starting ---------\n\n")

        self.add_message(prompt)

        for idx, agent in enumerate(self.agents):
            agent_a = self.agents[idx]
            agent_b = self.agents[idx + 1]

            print(
                f"\n\n--------- Running iteration {idx} with (agent_a: {agent_a.name}, agent_b: {agent_b.name}) ---------\n\n"
            )

            # agent_a -> chat -> agent_b
            if self.last_message_is_string:
                self.basic_chat(agent_a, agent_b, self.latest_message)

            # agent_a -> func() -> agent_b
            if self.last_message_is_func_call and self.has_functions(agent_a):
                self.function_chat(agent_a, agent_b, self.latest_message)

            self.spy_on_agents()

            if idx == self.total_agents - 2:
                if self.has_functions(agent_b):
                    # agent_b -> func() -> agent_b
                    self.self_function_chat(agent_b, self.latest_message)

                print(f"-------- Orchestrator Complete --------\n\n")

                was_successful = self.validate_results_func()

                self.spy_on_agents()

                cost, tokens = self.get_cost_and_tokens()

                return ConversationResult(
                    success=was_successful,
                    messages=self.messages,
                    cost=cost,
                    tokens=tokens,
                    last_message_str=self.last_message_always_string,
                )

    def broadcast_conversation(self, prompt: str) -> ConversationResult:
        """
        Broadcast a message from agent_a to all agents.

        For example
            "Agent A" -> "Agent B"
            "Agent A" -> "Agent C"
            "Agent A" -> "Agent D"
            "Agent A" -> "Agent E"
        """

        print(f"\n\n--------- {self.name} Orchestrator Starting ---------\n\n")

        self.add_message(prompt)

        broadcast_agent = self.agents[0]

        for idx, agent_iterate in enumerate(self.agents[1:]):
            print(
                f"\n\n--------- Running iteration {idx} with (agent_broadcast: {broadcast_agent.name}, agent_iteration: {agent_iterate.name}) ---------\n\n"
            )

            # agent_a -> chat -> agent_b
            if self.last_message_is_string:
                self.memory_chat(broadcast_agent, agent_iterate, prompt)

            # agent_b -> func() -> agent_b
            if self.last_message_is_func_call and self.has_functions(agent_iterate):
                self.function_chat(agent_iterate, agent_iterate, self.latest_message)

            self.spy_on_agents()

        print(f"-------- Orchestrator Complete --------\n\n")

        was_successful = self.validate_results_func()

        if was_successful:
            print(f"✅ Orchestrator was successful")
        else:
            print(f"❌ Orchestrator failed")

        cost, tokens = self.get_cost_and_tokens()

        return ConversationResult(
            success=was_successful,
            messages=self.messages,
            cost=cost,
            tokens=tokens,
            last_message_str=self.last_message_always_string,
        )
