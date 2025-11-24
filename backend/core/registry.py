"""
TrustChain Component Registry

Plugin registration system for dynamic discovery of:
- Evaluation strategies
- Analysis modules
- Output generators

Provides singleton registry, decorator registration, and component lookup.

Built with care by Kareem & Claude
"""

from typing import Any, Dict, List, Optional, Type
import logging

from .base import BaseComponent, BaseStrategy, BaseAnalyzer, BaseOutput, ComponentType

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """
    Registry for TrustChain plugins.

    Allows dynamic registration and discovery of strategies, analyzers,
    and output generators. Implements singleton pattern to ensure
    a single registry instance across the application.

    Usage:
        # Get the global registry
        registry = get_registry()

        # Register a component
        registry.register(MyStrategy)

        # Get a component instance
        strategy = registry.get_strategy("my_strategy", config={})

        # List all components
        components = registry.list_components()

    The registry also supports decorator-based registration:
        @register_component
        class MyStrategy(BaseStrategy):
            name = "my_strategy"
            ...
    """

    _instance: Optional["ComponentRegistry"] = None

    def __new__(cls) -> "ComponentRegistry":
        """Singleton pattern - ensure only one registry exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._strategies: Dict[str, Type[BaseStrategy]] = {}
            cls._instance._analyzers: Dict[str, Type[BaseAnalyzer]] = {}
            cls._instance._outputs: Dict[str, Type[BaseOutput]] = {}
            cls._instance._initialized = True
            logger.info("TrustChain ComponentRegistry initialized")
        return cls._instance

    def register(self, component_class: Type[BaseComponent]) -> None:
        """
        Register a component class.

        The component class must have a 'name' class attribute that
        serves as its unique identifier in the registry.

        Args:
            component_class: The component class to register

        Raises:
            ValueError: If component has no name or invalid type
        """
        # Create a temporary instance to get metadata
        # We pass empty config and skip validation for registration
        temp_instance = object.__new__(component_class)

        # Get name from class attribute
        name = getattr(component_class, 'name', None)
        if not name:
            raise ValueError(
                f"Component {component_class.__name__} must have a 'name' class attribute"
            )

        component_type = getattr(component_class, 'component_type', None)
        if not component_type:
            raise ValueError(
                f"Component {component_class.__name__} must have a 'component_type' class attribute"
            )

        if component_type == ComponentType.STRATEGY:
            if name in self._strategies:
                logger.warning(f"Overwriting existing strategy: {name}")
            self._strategies[name] = component_class
            logger.info(f"Registered strategy: {name}")

        elif component_type == ComponentType.ANALYZER:
            if name in self._analyzers:
                logger.warning(f"Overwriting existing analyzer: {name}")
            self._analyzers[name] = component_class
            logger.info(f"Registered analyzer: {name}")

        elif component_type == ComponentType.OUTPUT:
            if name in self._outputs:
                logger.warning(f"Overwriting existing output: {name}")
            self._outputs[name] = component_class
            logger.info(f"Registered output: {name}")

        else:
            raise ValueError(f"Unknown component type: {component_type}")

    def unregister(self, name: str, component_type: ComponentType) -> bool:
        """
        Unregister a component by name and type.

        Args:
            name: The component name
            component_type: The type of component

        Returns:
            True if component was removed, False if not found
        """
        if component_type == ComponentType.STRATEGY:
            if name in self._strategies:
                del self._strategies[name]
                logger.info(f"Unregistered strategy: {name}")
                return True
        elif component_type == ComponentType.ANALYZER:
            if name in self._analyzers:
                del self._analyzers[name]
                logger.info(f"Unregistered analyzer: {name}")
                return True
        elif component_type == ComponentType.OUTPUT:
            if name in self._outputs:
                del self._outputs[name]
                logger.info(f"Unregistered output: {name}")
                return True
        return False

    def get_strategy(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseStrategy:
        """
        Get an instance of a registered strategy.

        Args:
            name: The strategy name
            config: Optional configuration dictionary

        Returns:
            Configured strategy instance

        Raises:
            ValueError: If strategy not found
        """
        if name not in self._strategies:
            available = list(self._strategies.keys())
            raise ValueError(
                f"Unknown strategy: '{name}'. Available: {available}"
            )
        return self._strategies[name](config or {})

    def get_analyzer(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseAnalyzer:
        """
        Get an instance of a registered analyzer.

        Args:
            name: The analyzer name
            config: Optional configuration dictionary

        Returns:
            Configured analyzer instance

        Raises:
            ValueError: If analyzer not found
        """
        if name not in self._analyzers:
            available = list(self._analyzers.keys())
            raise ValueError(
                f"Unknown analyzer: '{name}'. Available: {available}"
            )
        return self._analyzers[name](config or {})

    def get_output(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseOutput:
        """
        Get an instance of a registered output generator.

        Args:
            name: The output generator name
            config: Optional configuration dictionary

        Returns:
            Configured output generator instance

        Raises:
            ValueError: If output generator not found
        """
        if name not in self._outputs:
            available = list(self._outputs.keys())
            raise ValueError(
                f"Unknown output: '{name}'. Available: {available}"
            )
        return self._outputs[name](config or {})

    def has_strategy(self, name: str) -> bool:
        """Check if a strategy is registered."""
        return name in self._strategies

    def has_analyzer(self, name: str) -> bool:
        """Check if an analyzer is registered."""
        return name in self._analyzers

    def has_output(self, name: str) -> bool:
        """Check if an output generator is registered."""
        return name in self._outputs

    def list_components(self) -> Dict[str, List[str]]:
        """
        List all registered components.

        Returns:
            Dictionary with keys 'strategies', 'analyzers', 'outputs'
            mapping to lists of component names
        """
        return {
            "strategies": list(self._strategies.keys()),
            "analyzers": list(self._analyzers.keys()),
            "outputs": list(self._outputs.keys()),
        }

    def get_component_metadata(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get metadata for all registered components.

        Returns:
            Dictionary with component types mapping to lists of metadata dicts
        """
        result = {
            "strategies": [],
            "analyzers": [],
            "outputs": [],
        }

        for name, cls in self._strategies.items():
            result["strategies"].append({
                "name": name,
                "class": cls.__name__,
                "description": getattr(cls, 'description', ''),
                "version": getattr(cls, 'version', '1.0.0'),
            })

        for name, cls in self._analyzers.items():
            result["analyzers"].append({
                "name": name,
                "class": cls.__name__,
                "description": getattr(cls, 'description', ''),
                "version": getattr(cls, 'version', '1.0.0'),
            })

        for name, cls in self._outputs.items():
            result["outputs"].append({
                "name": name,
                "class": cls.__name__,
                "description": getattr(cls, 'description', ''),
                "version": getattr(cls, 'version', '1.0.0'),
            })

        return result

    def clear(self) -> None:
        """
        Clear all registered components.

        Useful for testing or reconfiguration.
        """
        self._strategies.clear()
        self._analyzers.clear()
        self._outputs.clear()
        logger.info("ComponentRegistry cleared")


def register_component(cls: Type[BaseComponent]) -> Type[BaseComponent]:
    """
    Decorator to register a component class.

    Usage:
        @register_component
        class MyStrategy(BaseStrategy):
            name = "my_strategy"
            description = "My custom strategy"
            ...

    Args:
        cls: The component class to register

    Returns:
        The same class (unchanged)
    """
    ComponentRegistry().register(cls)
    return cls


def get_registry() -> ComponentRegistry:
    """
    Get the global ComponentRegistry instance.

    Returns:
        The singleton ComponentRegistry
    """
    return ComponentRegistry()
