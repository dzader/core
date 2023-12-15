"""Support for SleepIQ foundation preset selection."""
from __future__ import annotations

from asyncsleepiq import Side, SleepIQBed, SleepIQPreset, SleepIQFootWarmer, FootWarmingTemps

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SleepIQData, SleepIQDataUpdateCoordinator
from .entity import SleepIQBedEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SleepIQ foundation preset select entities."""
    data: SleepIQData = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for bed in data.client.beds.values():
        for preset in bed.foundation.presets:
            entities.append(
                SleepIQSelectEntity(
                    data.data_coordinator,
                    bed,
                    preset
                )
            )
        for foot_warmer in bed.foundation.foot_warmers:
            entities.append(
                SleepIQFootWarmingTempSelectEntity(
                    data.data_coordinator,
                    bed,
                    foot_warmer,
                )
            )
    async_add_entities(entities)

class SleepIQSelectEntity(SleepIQBedEntity[SleepIQDataUpdateCoordinator], SelectEntity):
    """Representation of a SleepIQ select entity."""

    def __init__(
        self,
        coordinator: SleepIQDataUpdateCoordinator,
        bed: SleepIQBed,
        preset: SleepIQPreset,
    ) -> None:
        """Initialize the select entity."""
        self.preset = preset

        self._attr_name = f"SleepNumber {bed.name} Foundation Preset"
        self._attr_unique_id = f"{bed.id}_preset"
        if preset.side != Side.NONE:
            self._attr_name += f" {preset.side_full}"
            self._attr_unique_id += f"_{preset.side.value}"
        self._attr_options = preset.options

        super().__init__(coordinator, bed)
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        """Update entity attributes."""
        self._attr_current_option = self.preset.preset

    async def async_select_option(self, option: str) -> None:
        """Change the current preset."""
        await self.preset.set_preset(option)
        self._attr_current_option = option
        self.async_write_ha_state()


class SleepIQFootWarmingTempSelectEntity(SleepIQBedEntity[SleepIQDataUpdateCoordinator], SelectEntity):
    """Representation of a SleepIQ foot warming temperatuer select entity."""

    def __init__(
        self,
        coordinator: SleepIQDataUpdateCoordinator,
        bed: SleepIQBed,
        foot_warmer: SleepIQFootWarmer,
    ) -> None:
        """Initialize the select entity."""
        self.foot_warmer = foot_warmer
        sleeper_name = next((sleeper.name for sleeper in bed.sleepers if sleeper.side == foot_warmer.side), foot_warmer.side.value)
        self._attr_name = f"SleepNumber {bed.name} {sleeper_name} Foot Warmer"
        self._attr_unique_id = f"{bed.id}-foot-warmer-{foot_warmer.side}"
        self._attr_options = [e.name.title() for e in FootWarmingTemps]
        super().__init__(coordinator, bed)
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        """Update entity attributes."""
        self._attr_current_option = FootWarmingTemps(self.foot_warmer.temperature).name.title()

    async def async_select_option(self, option: str) -> None:
        """Change the current preset."""
        temperature = FootWarmingTemps[option.upper()]
        timer = self.foot_warmer.timer or 120

        if option == FootWarmingTemps.OFF.name.title():
            await self.foot_warmer.turn_off()
        else:
            await self.foot_warmer.turn_on(temperature, timer)

        self._attr_current_option = option
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
