from .base import NamingStrategy
from .flat import FlatStrategy
from .mirror import MirrorStrategy
from .map_strategy import MapStrategy

STRATEGIES: dict[str, type[NamingStrategy]] = {
    "flat": FlatStrategy,
    "mirror": MirrorStrategy,
    "map": MapStrategy,
}


def get_strategy(name: str, **kwargs) -> NamingStrategy:
    """Returns an initialized NamingStrategy object matching the provided name.

    Args:
        name: The string identifier of the strategy in the STRATEGIES registry.
        **kwargs: Additional keyword arguments passed to the strategy's constructor.

    Returns:
        An initialized instance of a subclass of NamingStrategy.

    Raises:
        ValueError: If the specified name is not found in the registry.
    """
    strategy_class = STRATEGIES.get(name)
    if strategy_class is None:
        available = ", ".join(STRATEGIES.keys())
        raise ValueError(
            f"Unknown naming strategy '{name}'. Available: {available}"
        )
    return strategy_class(**kwargs)


def available_strategies() -> list[str]:
    """Provides the names of all available naming strategies.

    Returns:
        A list of string identifiers for the available strategies.
    """
    return list(STRATEGIES.keys())
