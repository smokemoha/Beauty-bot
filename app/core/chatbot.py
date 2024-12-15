from typing import Dict, List
from langchain.chains import ConversationChain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder
)

class BeautyServiceBot:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            temperature=0.7,
            openai_api_key=openai_api_key,
            model_name="gpt-4"
        )
        
        # self.services = {
        #     # "haircut": {"price": "50-100", "duration": "1 hour"},
        #     # "coloring": {"price": "100-200", "duration": "2-3 hours"},
        #     # "manicure": {"price": "30-50", "duration": "45 minutes"},
        #     # "pedicure": {"price": "40-60", "duration": "1 hour"},
        #     # "facial": {"price": "80-150", "duration": "1 hour"},
        #     # "massage": {"price": "70-120", "duration": "1 hour"}
        # }

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
        self.conversation = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            prompt=self.prompt,
            verbose=True
        )

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


    # def get_service_info(self, service_name: str) -> Dict:
    #     """Retrieve information about a specific service."""
    #     return self.services.get(service_name.lower(), None)

    # def list_services(self) -> List[str]:
    #     """Return a list of available services."""
    #     return list(self.services.keys())

    def process_message(self, message: str, language: str = "en") -> str:
        """
        Process incoming message and generate response.
        
        Args:
            message (str): The incoming message from the client
            language (str): Preferred language code ("en" for English, "ru" for Russian)
            
        Returns:
            str: Response message
        """
        # Add service information to the context
        context = {
            "input": message,
            "services": self.services
        }
        
        try:
            response = self.conversation.predict(**context)
            return response
        except Exception as e:
            return f"I apologize, but I encountered an error. Please try again. Error: {str(e)}"

    def reset_conversation(self):
        """Reset the conversation history."""
        self.memory.clear()

# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Initialize the bot
    anna_bot = BeautyServiceBot(openai_api_key=os.getenv("OPENAI_API_KEY"))
    
    # Example conversation
    messages = [
        "Hi, I'm interested in getting my hair done",
        "What kind of coloring services do you offer?",
        "How much does it cost?",
        "Can I book an appointment for next week?"
    ]
    
    for message in messages:
        response = anna_bot.process_message(message)
        print(f"\nClient: {message}")
        print(f"Anna: {response}")
