import json
from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import Iterable, Optional, TypedDict, Union

from openai import AsyncOpenAI, OpenAI
from openai.types.chat.chat_completion import ChatCompletion

from config import OPENAI_API_KEY
from constants import DEFAULT_OPENAI_SEED_VALUE, GPT_Model
from logger import loggerUtils as logger

OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)
ASYNC_OPENAI_CLIENT = AsyncOpenAI(api_key=OPENAI_API_KEY)


class AIGeneratorResponse(TypedDict):
    response: Union[str | dict | BaseModel]
    model: str
    input_tokens: int
    output_tokens: int
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None


class BaseGenerator(ABC):
    @abstractmethod
    def generate_response(self) -> AIGeneratorResponse:
        pass


class BaseGeneratorConfig(ABC):
    def __init__(self, **kwargs):
        self.set_params(**kwargs)

    def set_params(self, **kwargs):
        """Override this method to set the default configuration"""
        pass

    @classmethod
    def get_or_create(
        cls, config: Optional["BaseGeneratorConfig"] = None
    ) -> "BaseGeneratorConfig":
        try:
            if config:
                assert isinstance(config, cls), (
                    f"Invalid config type: {type(config)} != {cls.__name__}"
                )
                return config
            return cls()

        except AssertionError as e:
            logger.exception(f"Invalid Config set: {str(e)}")
            raise e


class VisionTextGenerator(BaseGenerator, ABC):
    """
    A class for generating text responses using LLM Vision APIs
    """

    pass


class OpenAI_Vision_Config(BaseGeneratorConfig):
    def set_params(self, **kwargs):
        self.model: str = kwargs.get("model", GPT_Model.GPT_4_1.value)
        self.fidelity: str = kwargs.get("fidelity", "low")
        self.max_tokens: Optional[int] = kwargs.get("max_tokens", None)
        self.temperature = kwargs.get("temperature", 0.3)
        self.seed = kwargs.get("seed", DEFAULT_OPENAI_SEED_VALUE)

        self.validate_params()

    def validate_params(self):
        try:
            assert self.fidelity in ["low", "high"], "Fidelity must be 'low' or 'high'"
            is_valid_model = self.model in GPT_Model.values()
            assert is_valid_model, f"Invalid model {self.model} selected"
        except AssertionError as e:
            logger.exception(f"Invalid OpenAI Vision Config set: {str(e)}")
            raise e


class OpenAIVisionTextGenerator(VisionTextGenerator):
    """
    A class for generating text responses using the OpenAI models with vision
    capabilities.

    Args:
        VisionTextGenerator (class): The base class for text generation.
    """

    # TODO: Add support for response_format(pydantic response) as done for
    # OpenAITextGenerator

    def __init__(self, config: Optional[OpenAI_Vision_Config] = None) -> None:
        self.config = OpenAI_Vision_Config.get_or_create(config)

    def generate_response(
        self,
        user_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        json_response: bool = False,
        image_file_urls: Optional[Iterable[str]] = None,
        base64_encoded_images: Optional[Iterable[bytes]] = None,
        project_name: Optional[str] = None,
        *args,
        **kwargs,
    ) -> AIGeneratorResponse:
        """
        Generates a text response based on the provided prompt.

        Args:
            `user_prompt` (Optional[str], optional): The input prompt for
                text generation. Defaults to None.

            `system_prompt` (Optional[str], optional): The system prompt
                for text generation. Defaults to None.

            `json_response` (bool, optional): Whether to return the response
                in JSON format. Defaults to False.

            `image_file_urls` (Optional[Iterable[str]], optional): URLs of
                images to be included in the prompt. Defaults to None.

            `base64_encoded_images` (Optional[Iterable[bytes]], optional):
                Base64-encoded images to be included in the prompt. Defaults
                to None.

            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: A dictionary containing the generated text response.
                The response is stored under the key "response".
        """
        response = self.generate_raw_response(
            user_prompt,
            system_prompt,
            json_response,
            image_file_urls,
            base64_encoded_images,
            *args,
            **kwargs,
        )

        return self._construct_response(response, json_response)

    def generate_raw_response(
        self,
        user_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        json_response: bool = False,
        image_file_urls: Optional[Iterable[str]] = None,
        base64_encoded_images: Optional[Iterable[bytes]] = None,
    ) -> ChatCompletion:
        """
        Generates a text response based on the provided prompt.
        """
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.json_response = json_response
        self.image_file_urls = image_file_urls
        self.base64_encoded_images = base64_encoded_images

        payload = self._create_payload()

        return OPENAI_CLIENT.chat.completions.create(**payload)

    def _parse_response_content(
        self,
        response: ChatCompletion,
        json_response: bool = False,
    ):
        _response_content = response.choices[0].message.content
        if json_response:
            _response_content = json.loads(_response_content)
        return _response_content

    def _construct_response(
        self, response: ChatCompletion, json_response: bool = False
    ) -> AIGeneratorResponse:
        return {
            "response": self._parse_response_content(response, json_response),
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "model": self.config.model,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
        }

    async def async_generate_response(
        self,
        user_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        json_response: bool = False,
        image_file_urls: Optional[Iterable[str]] = None,
        base64_encoded_images: Optional[Iterable[bytes]] = None,
        project_name: Optional[str] = None,
        *args,
        **kwargs,
    ) -> AIGeneratorResponse:
        response = await self.async_generate_raw_response(
            user_prompt,
            system_prompt,
            json_response,
            image_file_urls,
            base64_encoded_images,
            *args,
            **kwargs,
        )
        return self._construct_response(response, json_response)

    async def async_generate_raw_response(
        self,
        user_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        json_response: bool = False,
        image_file_urls: Optional[Iterable[str]] = None,
        base64_encoded_images: Optional[Iterable[bytes]] = None,
    ) -> ChatCompletion:
        """
        Generates a text response based on the provided prompt.
        """
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.json_response = json_response
        self.image_file_urls = image_file_urls
        self.base64_encoded_images = base64_encoded_images

        payload = self._create_payload()

        return await ASYNC_OPENAI_CLIENT.chat.completions.create(**payload)

    def _create_payload(self) -> dict:
        payload = dict()

        payload["model"] = self.config.model
        payload["messages"] = []
        payload["temperature"] = self.config.temperature
        payload["seed"] = self.config.seed

        if self.json_response:
            payload["response_format"] = {"type": "json_object"}

        if self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens

        system_prompt_payload = self.__create_system_prompt_payload()
        if system_prompt_payload:
            payload["messages"].append(system_prompt_payload)

        user_prompt_payload = self.__create_user_prompt_payload()
        if user_prompt_payload:
            payload["messages"].append(user_prompt_payload)

        return payload

    def __create_system_prompt_payload(self) -> Optional[dict]:
        return (
            {"role": "system", "content": self.system_prompt}
            if self.system_prompt
            else None
        )

    def __create_user_prompt_payload(self) -> Optional[dict]:
        return {"role": "user", "content": self.__create_user_content_payload()}

    def __create_user_content_payload(self):
        content = []

        if self.user_prompt:
            content.append({"type": "text", "text": self.user_prompt})

        if self.image_file_urls:
            for image_file_url in self.image_file_urls:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_file_url,
                            "detail": self.config.fidelity,
                        },
                    }
                )

        elif self.base64_encoded_images:
            for base64_encoded_image in self.base64_encoded_images:
                base64_image_link = f"data:image/jpeg;base64,{base64_encoded_image}"
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image_link,
                            "detail": self.config.fidelity,
                        },
                    }
                )

        else:
            raise ValueError(
                "Invalid request. "
                "Please provide either image_file_urls or "
                "base64_encoded_images."
            )

        return content


class OpenAI_Text_Config(BaseGeneratorConfig):
    """
    Configuration class for OpenAI text generation models.

    This class handles the configuration parameters for text-only OpenAI models.
    It inherits from BaseGeneratorConfig and implements parameter validation.
    """

    def set_params(self, **kwargs):
        """
        Sets the configuration parameters for the OpenAI text generator.

        Args:
            **kwargs: Arbitrary keyword arguments including:
                - model (str): The OpenAI model to use
                - max_tokens (int, optional): Maximum tokens in the response
                - temperature (float): Controls randomness in responses
                - seed (int): Seed for reproducible responses
        """
        self.model: str = kwargs.get("model", GPT_Model.GPT_40_MINI.value)
        self.max_tokens: Optional[int] = kwargs.get("max_tokens", None)
        self.temperature = kwargs.get("temperature", 0.3)
        self.seed = kwargs.get("seed", DEFAULT_OPENAI_SEED_VALUE)
        self.top_p = kwargs.get("top_p", None)
        self.frequency_penalty = kwargs.get("frequency_penalty", None)
        self.presence_penalty = kwargs.get("presence_penalty", None)

        self.validate_params()

    def validate_params(self):
        """
        Validates the configuration parameters.

        Raises:
            AssertionError: If any parameters are invalid
        """
        try:
            is_valid_model = self.model in GPT_Model.values()
            assert is_valid_model, f"Invalid model {self.model} selected"
        except AssertionError as e:
            logger.exception(f"Invalid OpenAI Text Config set: {str(e)}")
            raise e


class OpenAITextGenerator(BaseGenerator):
    """
    A class for generating text responses using OpenAI's text-only models.

    This class provides functionality for both synchronous and asynchronous
    text generation using OpenAI's API. It supports system and user prompts,
    and can return responses in both plain text and JSON formats.

    Args:
        config (Optional[OpenAI_Text_Config]): Configuration for the text
            generator. If None, default configuration will be used.
    """

    def __init__(self, config: Optional[OpenAI_Text_Config] = None) -> None:
        self.config: OpenAI_Text_Config = OpenAI_Text_Config.get_or_create(config)

    def generate_response(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        json_response: bool = False,
        project_name: Optional[str] = None,
        response_format: Optional[BaseModel] = None,
        *args,
        **kwargs,
    ) -> AIGeneratorResponse:
        """
        Generates a text response based on the provided prompts.

        Args:
            user_prompt (str): The input prompt for text generation
            system_prompt (Optional[str]): The system prompt for text
                generation. Defaults to None.
            json_response (bool): Whether to return the response in JSON
                format. Defaults to False.
            project_name (Optional[str]): Name of the project for logging
                purposes. Defaults to None.
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Returns:
            dict: A dictionary containing the generated text response and
                metadata including token usage and model information
        """
        response = self.generate_raw_response(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            json_response=json_response,
            response_format=response_format,
            *args,
            **kwargs,
        )

        return self._construct_response(response, json_response)

    def generate_raw_response(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        json_response: bool = False,
        response_format: Optional[BaseModel] = None,
    ) -> ChatCompletion:
        """
        Generates a raw API response based on the provided prompts.

        Args:
            user_prompt (str): The input prompt for text generation
            system_prompt (Optional[str]): The system prompt for text
                generation. Defaults to None.
            json_response (bool): Whether to return the response in JSON
                format. Defaults to False.

        Returns:
            ChatCompletion: The raw response from the OpenAI API
        """
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.json_response = json_response
        self.response_format = response_format

        payload = self._create_payload()

        # Use beta for custom response format since it's not supported in
        # stable
        if self.response_format is not None:
            return OPENAI_CLIENT.beta.chat.completions.parse(**payload)

        else:
            return OPENAI_CLIENT.chat.completions.create(**payload)

    def _parse_response_content(
        self,
        response: ChatCompletion,
        json_response: bool = False,
    ):
        """
        Parses the content from the API response.

        Args:
            response (ChatCompletion): The API response to parse
            json_response (bool): Whether to parse the response as JSON

        Returns:
            Union[str, dict]: The parsed response content
        """
        if self.response_format is not None:
            return response.choices[0].message.parsed

        else:
            _response_content = response.choices[0].message.content
            if json_response:
                _response_content = json.loads(_response_content)
            return _response_content

    def _construct_response(
        self, response: ChatCompletion, json_response: bool = False
    ) -> AIGeneratorResponse:
        """
        Constructs the final response dictionary.

        Args:
            response (ChatCompletion): The API response
            json_response (bool): Whether the response is in JSON format

        Returns:
            dict: The constructed response with metadata
        """
        return {
            "response": self._parse_response_content(response, json_response),
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "model": self.config.model,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
        }

    async def async_generate_response(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        json_response: bool = False,
        response_format: Optional[BaseModel] = None,
        project_name: Optional[str] = None,
        *args,
        **kwargs,
    ) -> AIGeneratorResponse:
        """
        Asynchronously generates a text response based on the provided prompts.

        Args:
            user_prompt (str): The input prompt for text generation
            system_prompt (Optional[str]): The system prompt for text
                generation. Defaults to None.
            json_response (bool): Whether to return the response in JSON
                format. Defaults to False.
            project_name (Optional[str]): Name of the project for logging
                purposes. Defaults to None.
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Returns:
            dict: A dictionary containing the generated text response and
                metadata including token usage and model information
        """
        response = await self.async_generate_raw_response(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            json_response=json_response,
            response_format=response_format,
            *args,
            **kwargs,
        )
        return self._construct_response(response, json_response)

    async def async_generate_raw_response(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        json_response: bool = False,
        response_format: Optional[BaseModel] = None,
    ) -> ChatCompletion:
        """
        Asynchronously generates a raw API response based on the provided prompts.

        Args:
            user_prompt (str): The input prompt for text generation
            system_prompt (Optional[str]): The system prompt for text
                generation. Defaults to None.
            json_response (bool): Whether to return the response in JSON
                format. Defaults to False.

        Returns:
            ChatCompletion: The raw response from the OpenAI API
        """
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.json_response = json_response
        self.response_format = response_format

        payload = self._create_payload()

        # Use beta for custom response format since it's not supported in
        # stable
        if self.response_format is not None:
            return await ASYNC_OPENAI_CLIENT.beta.chat.completions.parse(**payload)

        else:
            return await ASYNC_OPENAI_CLIENT.chat.completions.create(**payload)

    def _create_payload(self) -> dict:
        """
        Creates the payload for the API request.

        Returns:
            dict: The complete payload for the API request
        """
        payload = {
            "model": self.config.model,
            "messages": [],
            "temperature": self.config.temperature,
            "seed": self.config.seed,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
        }

        if self.json_response:
            payload["response_format"] = {"type": "json_object"}

        if self.response_format:
            payload["response_format"] = self.response_format

        if self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens

        if self.system_prompt:
            payload["messages"].append(
                {"role": "system", "content": self.system_prompt}
            )

        payload["messages"].append({"role": "user", "content": self.user_prompt})

        return payload