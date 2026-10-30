"""
AI Agronomist Chatbot Service

Provides intelligent agriculture-related responses.
Architecture supports plugging in an API-based LLM later
without changing the frontend.
"""

from typing import Optional, Dict, Any, List
import re


class ChatbotService:
    """
    AI Agronomist chatbot.

    Currently uses a rule-based knowledge base for common agriculture queries.
    The interface is designed so an LLM API (OpenAI, Google Gemini, etc.)
    can be connected later without changing the frontend.
    """

    KNOWLEDGE_BASE = {
        "disease": {
            "keywords": ["disease", "sick", "infected", "infection", "blight", "rot", "wilt", "rust", "mold", "spot", "mildew", "canker"],
            "responses": [
                "🌿 **Plant Disease Management**\n\nCommon plant diseases include:\n\n"
                "1. **Fungal Diseases**: Blight, rust, mold, mildew - treated with fungicides\n"
                "2. **Bacterial Diseases**: Bacterial spot, canker, wilt - remove infected parts, apply copper-based sprays\n"
                "3. **Viral Diseases**: Mosaic, leaf curl - control insect vectors, remove infected plants\n\n"
                "**Prevention Tips:**\n"
                "- Use disease-resistant varieties\n"
                "- Practice crop rotation\n"
                "- Maintain proper spacing for air circulation\n"
                "- Avoid overhead irrigation\n"
                "- Use clean, certified seeds\n\n"
                "Upload a leaf image in the Disease Detection module for AI-powered diagnosis!"
            ]
        },
        "pest": {
            "keywords": ["pest", "insect", "bug", "aphid", "worm", "caterpillar", "beetle", "mite", "fly", "thrip", "moth"],
            "responses": [
                "🐛 **Pest Management Guide**\n\n"
                "Common agricultural pests and solutions:\n\n"
                "| Pest | Crops Affected | Control Method |\n"
                "|------|---------------|----------------|\n"
                "| Aphids | Most crops | Neem oil, ladybugs, insecticidal soap |\n"
                "| Whitefly | Tomato, cotton | Yellow sticky traps, neem spray |\n"
                "| Armyworm | Corn, rice | Bt spray, hand-picking |\n"
                "| Spider Mites | Many crops | Miticides, water spray |\n"
                "| Thrips | Onion, garlic | Spinosad, blue sticky traps |\n\n"
                "**IPM (Integrated Pest Management) Strategy:**\n"
                "1. Monitor regularly\n"
                "2. Use biological controls first\n"
                "3. Chemical treatment as last resort\n"
                "4. Rotate chemicals to prevent resistance"
            ]
        },
        "soil": {
            "keywords": ["soil", "ph", "nitrogen", "phosphorus", "potassium", "npk", "nutrient", "fertility", "organic matter", "compost"],
            "responses": [
                "🌍 **Soil Health Guide**\n\n"
                "**Optimal Soil Parameters:**\n"
                "- **pH**: 6.0 - 7.5 (slightly acidic to neutral)\n"
                "- **Nitrogen (N)**: 20-50 kg/ha\n"
                "- **Phosphorus (P)**: 15-40 kg/ha\n"
                "- **Potassium (K)**: 20-45 kg/ha\n"
                "- **Moisture**: 30-70%\n\n"
                "**Improving Soil Health:**\n"
                "1. Add organic matter (compost, manure)\n"
                "2. Practice crop rotation\n"
                "3. Use cover crops\n"
                "4. Minimize tillage\n"
                "5. Test soil regularly\n\n"
                "Use the Soil Analysis module for detailed recommendations!"
            ]
        },
        "fertilizer": {
            "keywords": ["fertilizer", "fertiliser", "urea", "dap", "npk", "manure", "compost", "nutrient", "feed"],
            "responses": [
                "🧪 **Fertilizer Guide**\n\n"
                "**Common Fertilizers:**\n\n"
                "| Fertilizer | NPK Ratio | Best For |\n"
                "|-----------|-----------|----------|\n"
                "| Urea | 46-0-0 | Nitrogen boost |\n"
                "| DAP | 18-46-0 | Phosphorus boost |\n"
                "| MOP | 0-0-60 | Potassium boost |\n"
                "| NPK 10-10-10 | Balanced | General maintenance |\n"
                "| NPK 20-20-20 | Balanced | Flowering crops |\n\n"
                "**Application Tips:**\n"
                "- Apply based on soil test results\n"
                "- Split nitrogen application into 2-3 doses\n"
                "- Apply phosphorus as basal dose\n"
                "- Don't over-fertilize - it can harm plants and environment\n"
                "- Consider organic alternatives like compost and vermicompost"
            ]
        },
        "irrigation": {
            "keywords": ["irrigation", "water", "watering", "drip", "sprinkler", "flood", "moisture", "dry", "drought"],
            "responses": [
                "💧 **Smart Irrigation Guide**\n\n"
                "**Irrigation Methods:**\n\n"
                "1. **Drip Irrigation** (Most efficient)\n"
                "   - 90-95% water efficiency\n"
                "   - Best for: vegetables, orchards\n\n"
                "2. **Sprinkler Irrigation**\n"
                "   - 75-85% efficiency\n"
                "   - Best for: field crops, lawns\n\n"
                "3. **Flood/Furrow Irrigation**\n"
                "   - 50-60% efficiency\n"
                "   - Traditional, suitable for paddy\n\n"
                "**Scheduling Tips:**\n"
                "- Irrigate early morning or evening\n"
                "- Check soil moisture before irrigating\n"
                "- Adjust based on weather and crop stage\n"
                "- Use mulching to retain moisture"
            ]
        },
        "crop": {
            "keywords": ["crop", "plant", "grow", "sow", "harvest", "season", "variety", "seed", "planting"],
            "responses": [
                "🌾 **Crop Selection & Planning**\n\n"
                "**Season-wise Crop Guide:**\n\n"
                "🌞 **Kharif (Monsoon - June to October):**\n"
                "Rice, Corn, Cotton, Soybean, Groundnut, Millet\n\n"
                "❄️ **Rabi (Winter - October to March):**\n"
                "Wheat, Mustard, Potato, Peas, Gram\n\n"
                "☀️ **Zaid (Summer - March to June):**\n"
                "Watermelon, Muskmelon, Cucumber, Moong\n\n"
                "**Factors for Crop Selection:**\n"
                "1. Soil type and pH\n"
                "2. Available water resources\n"
                "3. Climate and season\n"
                "4. Market demand\n"
                "5. Previous crop grown (rotation)\n\n"
                "Use the Soil Analysis module to get personalized crop recommendations!"
            ]
        },
        "weather": {
            "keywords": ["weather", "rain", "temperature", "heat", "cold", "frost", "drought", "flood", "climate", "monsoon"],
            "responses": [
                "🌤️ **Weather-Based Farming Tips**\n\n"
                "**Hot Weather (>35°C):**\n"
                "- Increase irrigation frequency\n"
                "- Apply mulch to retain moisture\n"
                "- Provide shade for sensitive crops\n"
                "- Avoid spraying during peak heat\n\n"
                "**Cold Weather (<10°C):**\n"
                "- Protect from frost with covers\n"
                "- Delay transplanting\n"
                "- Apply organic mulch for insulation\n\n"
                "**Rainy Season:**\n"
                "- Ensure proper drainage\n"
                "- Watch for fungal diseases\n"
                "- Reduce irrigation schedule\n"
                "- Apply preventive fungicides\n\n"
                "Check the Data Acquisition module for real-time weather data!"
            ]
        },
        "yield": {
            "keywords": ["yield", "production", "harvest", "output", "productivity", "tons", "quintal"],
            "responses": [
                "📊 **Maximizing Crop Yield**\n\n"
                "**Key Factors for High Yield:**\n\n"
                "1. **Soil Health**: Regular testing, balanced fertilization\n"
                "2. **Quality Seeds**: Use certified, high-yielding varieties\n"
                "3. **Water Management**: Optimal irrigation scheduling\n"
                "4. **Pest & Disease Control**: Regular monitoring, timely action\n"
                "5. **Proper Spacing**: Follow recommended plant spacing\n"
                "6. **Timely Operations**: Sow and harvest at the right time\n"
                "7. **Weed Management**: Keep fields weed-free\n\n"
                "Use the Crop Yield Prediction module for AI-powered yield estimates!"
            ]
        },
        "greeting": {
            "keywords": ["hello", "hi", "hey", "good morning", "good evening", "help", "start"],
            "responses": [
                "👋 **Hello! I'm your AI Agronomist Assistant.**\n\n"
                "I can help you with:\n\n"
                "🌿 **Crop Health** - Disease identification and treatment\n"
                "🐛 **Pest Control** - Pest management strategies\n"
                "🌍 **Soil Analysis** - Soil health and fertilizer advice\n"
                "💧 **Irrigation** - Smart watering schedules\n"
                "🌾 **Crop Selection** - What to grow and when\n"
                "🌤️ **Weather** - Weather-based farming tips\n"
                "📊 **Yield** - Maximizing crop productivity\n\n"
                "**Just type your question and I'll provide expert guidance!**\n\n"
                "You can also use the platform's modules for:\n"
                "- 📸 Disease Detection (upload leaf images)\n"
                "- 🧪 Soil Analysis (enter soil parameters)\n"
                "- 📈 Yield Prediction (get crop estimates)"
            ]
        }
    }

    def get_response(self, message: str) -> str:
        """
        Generate a response to the user's agriculture query.

        This method can be replaced with an LLM API call without
        changing the interface.
        """
        message_lower = message.lower().strip()

        # Find the best matching topic
        best_match = None
        best_score = 0

        for topic, data in self.KNOWLEDGE_BASE.items():
            score = sum(1 for kw in data["keywords"] if kw in message_lower)
            if score > best_score:
                best_score = score
                best_match = topic

        if best_match and best_score > 0:
            import random
            responses = self.KNOWLEDGE_BASE[best_match]["responses"]
            return responses[0] if responses else self._default_response()
        else:
            return self._default_response()

    def _default_response(self) -> str:
        """Default response when no topic matches."""
        return (
            "🌱 **I'd be happy to help with your farming question!**\n\n"
            "I specialize in:\n"
            "- 🌿 Plant diseases and treatments\n"
            "- 🐛 Pest identification and control\n"
            "- 🌍 Soil health and fertilizers\n"
            "- 💧 Irrigation and water management\n"
            "- 🌾 Crop selection and planning\n"
            "- 🌤️ Weather-based farming tips\n"
            "- 📊 Yield optimization\n\n"
            "Try asking something like:\n"
            "- *'How do I treat blight in tomatoes?'*\n"
            "- *'What fertilizer should I use for wheat?'*\n"
            "- *'When should I irrigate my rice field?'*\n"
            "- *'What crops can I grow in winter?'*"
        )


# Singleton instance
chatbot_service = ChatbotService()
