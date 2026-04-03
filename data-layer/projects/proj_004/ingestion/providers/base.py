"""
Provider 抽象基类
新增数据来源只需继承此类并实现 fetch() 和 provider_id。
"""
from abc import ABC, abstractmethod
from ingestion.models import RawRecord


class ProviderAdapter(ABC):
    """
    所有数据来源适配器的抽象基类。
    未来新增数据源（RSS、API、人工录入等）只需新建文件实现此接口，
    不改 Normalizer / Exporter / CLI 任何代码。
    """

    @abstractmethod
    def fetch(self, **kwargs) -> list[RawRecord]:
        """
        拉取数据，返回 RawRecord 列表。
        kwargs 由各 Provider 自行定义（如 date、date_range、limit 等）。
        """
        ...

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Provider 唯一标识，写入 ingestion_meta.provider"""
        ...
