from typing import Dict, List
# from langchain.chains import ConversationChain
from langchain import memory
from langchain.chains.llm import LLMChain
# from langchain.chat_models import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder
)

class BeautyServiceBot:
    def __init__(self, api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            api_key=api_key,
            model="gemini-1.5-pro"
        )
    

        self.services = [
            {"category": "Manicure", "name": "Gel polish removal (with membership card)", "price_from": "133 P"},
            {"category": "Manicure", "name": "Gel polish removal (without membership card)", "price_from": "400 P"},
            {"category": "Manicure", "name": "Manicure (with membership card)", "price_from": "733 P"},
            {"category": "Manicure", "name": "Manicure (without membership card)", "price_from": "1,100 P"},
            {"category": "Manicure", "name": "Gel polish application (hands, with membership card)", "price_from": "800 P"},
            {"category": "Manicure", "name": "Gel polish application (hands, without membership card)", "price_from": "1,200 P"},
            {"category": "Manicure", "name": "Gel application", "price_from": "1,700 P"},
            {"category": "Manicure", "name": "Nail polish application (hands)", "price_from": "500 P"},
            {"category": "Manicure", "name": "Nail polish removal (hands)", "price_from": "50 P"},
            {"category": "Manicure", "name": "Children's manicure + regular polish application", "price_from": "1,500 P"},
            {"category": "Manicure", "name": "One-hour manicure", "price_from": "2,600 P"},
            {"category": "Manicure", "name": "Men's manicure", "price_from": "1,200 P"},
            {"category": "Design", "name": "Design 500", "price_from": "500 P"},
            {"category": "Design", "name": "Design 1000", "price_from": "1,000 P"},
            {"category": "Design", "name": "Design 300", "price_from": "300 P"},
            {"category": "Design", "name": "Artistic painting", "price_from": "150 P"},
        ]
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self._initialize_prompt_template()
        self._setup_conversation_chain()

    def _initialize_prompt_template(self):
        system_template = """You are Anna, a charismatic and confident beauty salon owner. Your personality traits:

        - Sociable, confident, and charismatic
        - Use natural, slightly informal language with occasional humor
        - Focus on helping clients enhance their beauty
        - Passionate about beauty industry and artistry
        - Skilled at engaging clients and selling services

        Guidelines for interaction:
        - Communicate in both Russian and English (match the client's language)
        - Share relevant experiences and propose beauty solutions
        - Ask leading sales questions to guide the conversation
        - Redirect off-topic discussions back to beauty services
        - Adapt communication style based on client's gender (identified through names)
        - Maintain professional yet friendly tone
        - Avoid excessive punctuation and emojis

        Available services: {services}

        Current conversation history: {chat_history}
        Human: {input}
        Assistant: Let's respond appropriately to help the client..."""

        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])

    def _setup_conversation_chain(self):
        self.conversation = self.prompt | self.llm

    def get_service_info(self, service_name: str) -> Dict:
        """Retrieve information about a specific service by its name."""
        service_name_lower = service_name.lower()
        for service in self.services:
            if service["name"].lower() == service_name_lower:
                return service
        return None

    def list_services(self) -> List[str]:
        """Return a list of all available service names."""
        return [service["name"] for service in self.services]


    # def process_message(self, message: str, language: str = "en") -> str:
    #     """
    #     Process incoming message and generate response.
        
    #     Args:
    #         message (str): The incoming message from the client
    #         language (str): Preferred language code ("en" for English, "ru" for Russian)
            
    #     Returns:
    #         str: Response message
    #     """
    #     # Load the chat history from memory
    #     history_context = self.memory.load_memory_variables({})

    #     # Prepare the input to the pipeline
    #     # We must provide "services", "input", and "chat_history" as required by the prompt.
    #     try:
    #         response_message = self.conversation.invoke({
    #             "input": message,
    #             "services": self.services,
    #             "chat_history": history_context["chat_history"]
    #         })

    #         # response_message is a BaseMessage. Get the content:
    #         response_text = response_message.content
            
    #         # Save the turn to memory
    #         self.memory.save_context({"input": message}, {"output": response_text})

    #         return response_text
    #     except Exception as e:
    #         return f"I apologize, but I encountered an error. Please try again. Error: {str(e)}"

    def process_message(self, message: str, language: str = "en") -> Dict:
        history_context = self.memory.load_memory_variables({})
        response = {"text": "", "action": None}

        try:
            response_message = self.conversation.invoke({
                "input": message,
                "services": self.services,
                "chat_history": history_context["chat_history"]
            })
            response_text = response_message.content
            self.memory.save_context({"input": message}, {"output": response_text})

            # # Detect booking intent
            # Check if a service recommendation exists in the response
            for service in self.services:
                if service["name"].lower() in response_text.lower():
                    response["action"] = {
                        "type": "book",
                        "service": service["name"]
                    }
                    break

            response["text"] = response_text
        except Exception as e:
            response["text"] = f"Error: {str(e)}"
        return response


    def reset_conversation(self):
        """Reset the conversation history."""
        self.memory.clear()
