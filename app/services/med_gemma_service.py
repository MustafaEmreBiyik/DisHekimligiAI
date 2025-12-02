import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedGemmaService:
    """
    Service to interact with High-Reasoning LLMs via Hugging Face Inference API
    for medical validation.
    """
    
    def __init__(self):
        self.api_key = self._get_api_key_robust()
        
        if not self.api_key:
            raise ValueError(
                "HUGGINGFACE_API_KEY not found! "
                "Please ensure you have a .env file in the project root with this key."
            )
        
        # Using Gemma 2 9B IT for its strong reasoning capabilities
        self.model_id = "google/gemma-2-9b-it"
        self.client = InferenceClient(token=self.api_key)

    def _get_api_key_robust(self) -> Optional[str]:
        """
        Attempts to find the API key using multiple methods to handle Windows encoding issues.
        """
        # 1. Try standard environment variable first
        base_dir = Path(__file__).resolve().parent.parent.parent
        env_path = base_dir / ".env"
        
        # Force reload to be sure
        load_dotenv(dotenv_path=env_path, override=True)

        key = os.getenv("HUGGINGFACE_API_KEY")
        if key:
            return key.strip()

        # 2. Manual file parsing (Fallback for Windows encoding issues)
        if not env_path.exists():
            logger.error(f".env file not found at {env_path}")
            return None

        # Try common encodings to read the file manually
        encodings_to_try = ["utf-8-sig", "utf-8", "latin-1"]
        
        for encoding in encodings_to_try:
            try:
                content = env_path.read_text(encoding=encoding)
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    if "HUGGINGFACE_API_KEY" in line and "=" in line:
                        parts = line.split("=", 1)
                        found_key = parts[1].strip().strip('"').strip("'")
                        logger.info(f"API Key loaded via manual parsing ({encoding})")
                        return found_key
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Error reading .env with {encoding}: {e}")

        return None

    def validate_clinical_action(self, student_text: str, rules: Dict[str, Any], context_summary: str) -> Dict[str, Any]:
        """
        Validates a student's action against clinical rules using the LLM.
        
        Args:
            student_text: The action proposed by the student.
            rules: A dictionary of clinical rules.
            context_summary: A summary of the patient case context.
            
        Returns:
            A dictionary containing validation results.
        """
        
        system_prompt = f"""
        You are a Senior Oral Pathology Examiner. Validate the student's clinical decision based strictly on the provided rules.
        
        CASE CONTEXT:
        {context_summary}
        
        MANDATORY CLINICAL RULES:
        {json.dumps(rules, indent=2)}
        
        STUDENT ACTION:
        "{student_text}"
        
        EVALUATION TASK:
        1. Check if the student action violates any "contraindications" in the rules.
        2. Check if the student missed any "required_history" or "required_exam".
        3. Determine if the action is safe.

        OUTPUT FORMAT:
        Return ONLY a JSON object. Do not explain outside the JSON.
        {{
            "is_clinically_accurate": boolean,
            "safety_violation": boolean,
            "missing_critical_info": ["list", "of", "missing", "items"],
            "feedback": "Professional feedback explaining the mistake or confirming the correct action."
        }}
        """

        messages = [{"role": "user", "content": system_prompt}]
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat_completion(
                    model=self.model_id,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.1, # Low temperature for consistent JSON
                )
                
                content = response.choices[0].message.content.strip()
                
                # Clean Markdown formatting if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                result = json.loads(content)
                
                # Validate structure
                required_keys = ["is_clinically_accurate", "safety_violation", "missing_critical_info", "feedback"]
                if all(key in result for key in required_keys):
                    return result
                else:
                    raise ValueError("Missing required keys in LLM response")

            except Exception as e:
                logger.warning(f"Validation attempt {attempt + 1} failed: {e}")
                time.sleep(1)

        logger.error("All validation attempts failed.")
        
        # Fail-safe response
        return {
            "is_clinically_accurate": False,
            "safety_violation": False,
            "missing_critical_info": [],
            "feedback": "System Error: Unable to validate response at this time. Please try again."
        }

if __name__ == "__main__":
    # Test block for verification
    print("Initializing MedGemmaService Test...")
    try:
        service = MedGemmaService()
        
        test_rules = {
            "contraindications": ["Do not prescribe corticosteroids for undiagnosed ulcerative lesions"],
            "required_history": ["Duration of lesion"],
            "required_exam": ["Palpation"]
        }
        
        test_context = "55-year-old male with indurated ulcer on tongue for 4 weeks."
        test_student_input = "I will prescribe triamcinolone acetonide."
        
        print(f"\nContext: {test_context}")
        print(f"Student Action: {test_student_input}")
        print("\nValidating...")
        
        result = service.validate_clinical_action(test_student_input, test_rules, test_context)
        print("\nValidation Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        logger
