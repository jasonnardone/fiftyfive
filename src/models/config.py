"""Configuration schema models using Pydantic"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    write_rps: int = Field(default=10, ge=1, le=100)
    read_rps: int = Field(default=20, ge=1, le=100)
    burst_size: int = Field(default=5, ge=1)


class ExchangeConfig(BaseModel):
    """Exchange API configuration"""
    name: str = Field(default="kalshi")
    api_base_url: str
    ws_url: str
    api_key_id: str
    private_key_path: str
    rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig)


class RiskConfig(BaseModel):
    """Risk management limits"""
    max_exposure_per_market: float = Field(gt=0)
    max_total_exposure: float = Field(gt=0)
    max_contracts_per_side: int = Field(default=20, ge=1)
    daily_loss_limit: float = Field(gt=0)
    error_rate_threshold: float = Field(default=0.10, ge=0, le=1)
    consecutive_losses: int = Field(default=5, ge=1)
    inventory_target: int = Field(default=0)
    max_inventory_skew: int = Field(default=10, ge=1)
    unwind_threshold: float = Field(default=0.80, ge=0, le=1)


class MarketFilterConfig(BaseModel):
    """Market selection filters"""
    min_daily_volume: float = Field(default=10000, ge=0)
    max_spread: float = Field(default=0.10, ge=0, le=1)
    categories: List[str] = Field(default_factory=lambda: ["sports"])


class PricingConfig(BaseModel):
    """Pricing strategy configuration"""
    model: str = Field(default="mid_price_skew")
    spread_calculation: str = Field(default="dynamic")
    base_spread: float = Field(ge=0.01, le=0.50)
    min_spread: Optional[float] = Field(default=None, ge=0.01)
    max_spread: Optional[float] = Field(default=None, ge=0.01, le=1.0)
    inventory_adjustment: bool = Field(default=True)
    inventory_multiplier: float = Field(default=1.5, ge=1.0)
    volatility_adjustment: bool = Field(default=True)
    volatility_multiplier: float = Field(default=2.0, ge=1.0)

    @field_validator('max_spread')
    def validate_max_spread(cls, v, info):
        """Ensure max_spread >= min_spread"""
        min_spread = info.data.get('min_spread')
        if v is not None and min_spread is not None and v < min_spread:
            raise ValueError(f"max_spread ({v}) must be >= min_spread ({min_spread})")
        return v


class OrderSizingConfig(BaseModel):
    """Order sizing configuration"""
    method: str = Field(default="fixed")
    base_size: int = Field(ge=1)
    max_size: int = Field(ge=1)

    @field_validator('max_size')
    def validate_max_size(cls, v, info):
        """Ensure max_size >= base_size"""
        base_size = info.data.get('base_size')
        if base_size and v < base_size:
            raise ValueError(f"max_size ({v}) must be >= base_size ({base_size})")
        return v


class StrategyConfig(BaseModel):
    """Trading strategy configuration"""
    name: str
    market_filters: MarketFilterConfig = Field(default_factory=MarketFilterConfig)
    pricing: PricingConfig
    order_sizing: OrderSizingConfig


class ExecutionConfig(BaseModel):
    """Order execution configuration"""
    default_order_type: str = Field(default="limit")
    stp_enabled: bool = Field(default=True)
    stp_cancel_delay: float = Field(default=0.05, ge=0.01, le=1.0)
    order_refresh_interval: int = Field(default=10, ge=1)
    always_quoted: bool = Field(default=True)
    quote_both_sides: bool = Field(default=True)


class WebSocketConfig(BaseModel):
    """WebSocket connection configuration"""
    auto_reconnect: bool = Field(default=True)
    reconnect_delay: int = Field(default=5, ge=1)
    max_reconnect_attempts: int = Field(default=10, ge=1)
    heartbeat_interval: int = Field(default=30, ge=10)
    snapshot_refresh_interval: int = Field(default=30, ge=10)


class OrderBookConfig(BaseModel):
    """Order book configuration"""
    depth_levels: int = Field(default=10, ge=1)
    staleness_threshold: int = Field(default=60, ge=10)


class DataConfig(BaseModel):
    """Data streaming configuration"""
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)
    orderbook: OrderBookConfig = Field(default_factory=OrderBookConfig)


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO")
    log_dir: str = Field(default="logs/")
    log_rotation: str = Field(default="daily")
    retention_days: int = Field(default=30, ge=1)


class AlertsConfig(BaseModel):
    """Alerting configuration"""
    slack_enabled: bool = Field(default=False)
    email_enabled: bool = Field(default=False)
    terminal_enabled: bool = Field(default=True)


class MonitoringConfig(BaseModel):
    """Monitoring configuration"""
    enabled: bool = Field(default=True)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)


class AdvancedConfig(BaseModel):
    """Advanced configuration"""
    dry_run: bool = Field(default=False)
    use_connection_pooling: bool = Field(default=True)
    max_concurrent_requests: int = Field(default=50, ge=1)
    request_timeout: int = Field(default=10, ge=1)


class Config(BaseModel):
    """Root configuration model"""
    version: str
    environment: str
    exchange: ExchangeConfig
    risk: RiskConfig
    strategy: StrategyConfig
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)

    @field_validator('environment')
    def validate_environment(cls, v):
        """Validate environment"""
        if v not in ('production', 'demo', 'staging'):
            raise ValueError(f"Environment must be production, demo, or staging, got {v}")
        return v
