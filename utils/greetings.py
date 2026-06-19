# Edit this file to add new greeting types, keywords, or responses!
# This separates greeting configurations from the core RAG logic.

GREETINGS_MAP = [
    {
        "name": "standard",
        "keywords": ["hi", "hello", "hey", "greetings", "hii", "hiii", "helloo"],
        "default_reply": "Hello! Welcome to Aaj Tech Trading. How can I help you today?"
    },
    {
        "name": "morning",
        "keywords": ["good morning", "morning", "gud morning", "gud mrng"],
        "default_reply": "Good morning! Welcome to Aaj Tech Trading. How can I help you today?"
    },
    {
        "name": "afternoon",
        "keywords": ["good afternoon", "afternoon", "gud afternoon"],
        "default_reply": "Good afternoon! Welcome to Aaj Tech Trading. How can I help you today?"
    },
    {
        "name": "evening",
        "keywords": ["good evening", "evening", "gud evening"],
        "default_reply": "Good evening! Welcome to Aaj Tech Trading. How can I help you today?"
    },
    {
        "name": "casual",
        "keywords": ["whats up", "whatsup", "sup", "yo"],
        "default_reply": "Hey there! How can I help you today?"
    },
    {
        "name": "hindi",
        "keywords": ["namaste", "pranam", "ram ram", "radhe radhe"],
        "default_reply": "Namaste! Aaj Tech Trading mein aapka swagat hai. Aaj hum aapki kya madad kar sakte hain?"
    }
]
