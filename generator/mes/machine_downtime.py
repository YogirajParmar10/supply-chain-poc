from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from generator.config.settings import MachineDowntimeSettings, NoiseSettings
from generator.mes.noise import apply_machine_downtime_noise
from generator.transactional.common import generate_order_dates, status_choices
from generator.utils.ids import format_id


def _plant_ids(plants: pd.DataFrame) -> list[str]:
    if plants.empty:
        raise ValueError("No plants found in plants master data")
    return plants["plant_id"].tolist()


def _machine_names(settings: MachineDowntimeSettings) -> list[str]:
    return [
        f"{machine_type} {number}"
        for machine_type in settings.machine_types
        for number in range(1, settings.machines_per_plant + 1)
    ]


def generate_machine_downtime(
    plants: pd.DataFrame,
    settings: MachineDowntimeSettings,
    rng: np.random.Generator,
    noise_settings: NoiseSettings | None = None,
    *,
    id_start: int = 1,
) -> pd.DataFrame:
    plant_ids = _plant_ids(plants)
    machine_names = _machine_names(settings)
    reasons, reason_weights = status_choices(settings.reason_weights)

    start_dates = generate_order_dates(
        settings.count,
        settings.resolved_start_date,
        settings.resolved_end_date,
        rng,
    )
    start_seconds = rng.integers(0, 24 * 3600, size=settings.count)
    durations_minutes = rng.integers(
        settings.min_duration_minutes,
        settings.max_duration_minutes + 1,
        size=settings.count,
    )
    selected_plants = rng.choice(plant_ids, size=settings.count)
    selected_machines = rng.choice(machine_names, size=settings.count)
    selected_reasons = rng.choice(reasons, size=settings.count, p=reason_weights)

    rows = []
    for index in range(settings.count):
        start_time = datetime.combine(start_dates[index], datetime.min.time()) + timedelta(
            seconds=int(start_seconds[index])
        )
        end_time = start_time + timedelta(minutes=int(durations_minutes[index]))
        rows.append(
            {
                "downtime_id": format_id("DT", id_start + index, 6),
                "plant_id": selected_plants[index],
                "machine_name": selected_machines[index],
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "reason": selected_reasons[index],
            }
        )

    machine_downtime = pd.DataFrame(rows)
    if noise_settings is None:
        return machine_downtime

    return apply_machine_downtime_noise(machine_downtime, plants, noise_settings, rng)
