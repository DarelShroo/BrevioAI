import os
import time
from openai import OpenAI
from ..constants.constants import Constants
from ..constants.summary_messages import SummaryMessages
from ..enums.role import RoleType
from ..managers.directory_manager import DirectoryManager
from ..models.config_model import ConfigModel as Config
from ..models.response_model import SummaryResponse
class Summary:
    def __init__(self, transcription_path, summary_path, content, config: Config):
        self.transcription_path = transcription_path
        self.summary_path = summary_path
        self.content = content
        self.config = config

        self.api_key = self.config.api_key
        self.max_tokens = self.config.max_tokens
        self.tokens_per_minute = self.config.tokens_per_minute
        self.temperature = self.config.temperature

        self.client = OpenAI(api_key=self.api_key)

        self.model =  config.model.value


    def generate_summary(self):
        try:
            directory_manager = DirectoryManager(self.config)
            directory_manager.validate_paths(self.transcription_path)
            
            transcription = directory_manager.read_transcription(self.transcription_path)
            
            chunks = [
                transcription[i:i + int(self.max_tokens)] 
                for i in range(0, len(transcription), int(self.max_tokens))
            ]

            summary = ""
            total_tokens_used = 0

            for chunk in chunks:
                if total_tokens_used + int(self.max_tokens) > int(self.tokens_per_minute):
                    print(SummaryMessages.WAITING)
                    time.sleep(60)
                    total_tokens_used = 0 

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": RoleType.SYSTEM.value, "content": self.content},
                        {"role": RoleType.USER.value, "content": chunk}
                    ],
                    max_tokens=int(self.max_tokens),
                    temperature=float(self.temperature)
                )

                summary += response.choices[0].message.content.strip()
                total_tokens_used += int(self.max_tokens)

            directory_manager.write_summary(summary, self.summary_path)

            return SummaryResponse(
                True, 
                str(summary),
                str(SummaryMessages.WRITE_SUMMARY.format(self.summary_path))
            )

        except Exception as e:
            return SummaryResponse(
                False, 
                f"Error occurred: {str(e)}",
                SummaryMessages.ERROR_GENERATING_SUMMARY.format(str(e))
            )
            
             
