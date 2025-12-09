# Графік відключень електроенергії Чернівецької області

[![CI](https://github.com/maxbanton/ha-cv-power-outages/actions/workflows/ci.yml/badge.svg)](https://github.com/maxbanton/ha-cv-power-outages/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

> **НЕОФІЦІЙНА ІНТЕГРАЦІЯ** - Це громадський проект, який НЕ пов'язаний з енергетичною компанією. Використовуйте на власний ризик.

Інтеграція для Home Assistant, яка показує графік відключень електроенергії для Чернівецької області. Дані отримуються з публічно доступної інформації.

## Можливості

- **Поточний стан** - Показує чи є зараз світло (on/off)
- **Наступне включення** - Час коли світло включать
- **Наступне відключення** - Час коли світло виключать

> Стан "можливо є" (maybe) вважається як "є світло" (on)

## Встановлення

### HACS (Рекомендовано)

1. Відкрийте HACS в Home Assistant
2. Натисніть "Integrations"
3. Натисніть меню (три крапки) → "Custom repositories"
4. Додайте URL цього репозиторію, виберіть категорію "Integration"
5. Натисніть "Add"
6. Знайдіть "Chernivtsi Power Schedule" та встановіть
7. Перезапустіть Home Assistant

### Ручне встановлення

1. Завантажте папку `custom_components/cv_oblenergo` з цього репозиторію
2. Скопіюйте її в директорію `custom_components` вашого Home Assistant
3. Перезапустіть Home Assistant

## Налаштування

1. Перейдіть в **Settings** → **Devices & Services**
2. Натисніть **+ Add Integration**
3. Знайдіть "Chernivtsi Power Schedule"
4. Виберіть номер вашої групи (1-12)

### Як дізнатися номер групи

Відвідайте [oblenergo.cv.ua/shutdowns-search](https://oblenergo.cv.ua/shutdowns-search/) для пошуку вашої групи:
1. Виберіть дільницю
2. Введіть населений пункт
3. Введіть вулицю
4. Введіть номер будинку

Результати пошуку покажуть номер вашої групи.

## Сутності (Entities)

| Сутність | Тип | Опис |
|----------|-----|------|
| `sensor.cv_power_state` | Sensor | Поточний стан: `on` або `off` |
| `sensor.cv_power_next_on` | Sensor | Час наступного включення |
| `sensor.cv_power_next_off` | Sensor | Час наступного відключення |

### Атрибути сенсора стану

Сенсор `sensor.cv_power_state` має додаткові атрибути:

| Атрибут | Опис |
|---------|------|
| `schedule_date` | Дата графіку (YYYY-MM-DD) |
| `group` | Номер групи |
| `hours_with_power` | Заплановано годин зі світлом |
| `hours_without_power` | Заплановано годин без світла |

## Застереження

**ЦЕ НЕОФІЦІЙНА ІНТЕГРАЦІЯ.**

- Цей проект НЕ пов'язаний з енергетичною компанією
- Дані графіку отримуються з публічних джерел і можуть змінюватися
- Інтеграція надається "як є" без гарантій
- Завжди перевіряйте критичну інформацію на офіційних джерелах

---

# Chernivtsi Power Schedule - Home Assistant Integration

[English version]

> **UNOFFICIAL INTEGRATION** - This is a community project and is NOT affiliated with any electricity company. Use at your own risk.

Home Assistant integration for power outage schedule in Chernivtsi region, Ukraine.

## Features

- **Current state** - Shows if electricity is currently on or off
- **Next ON time** - When power will be turned on
- **Next OFF time** - When power will be turned off

> "Maybe" state is treated as "on"

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots menu and select "Custom repositories"
4. Add this repository URL and select "Integration" as the category
5. Click "Add"
6. Search for "Chernivtsi Power Schedule" and install it
7. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/cv_oblenergo` folder from this repository
2. Copy it to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Chernivtsi Power Schedule"
4. Select your group number (1-12)

### Finding Your Group Number

Visit [oblenergo.cv.ua/shutdowns-search](https://oblenergo.cv.ua/shutdowns-search/) to find your group by address.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.cv_power_state` | Sensor | Current state: `on` or `off` |
| `sensor.cv_power_next_on` | Sensor | Timestamp of next power ON |
| `sensor.cv_power_next_off` | Sensor | Timestamp of next power OFF |

### State Sensor Attributes

The `sensor.cv_power_state` sensor has additional attributes:

| Attribute | Description |
|-----------|-------------|
| `schedule_date` | Schedule date (YYYY-MM-DD) |
| `group` | Group number |
| `hours_with_power` | Planned hours with electricity |
| `hours_without_power` | Planned hours without electricity |

## Development

### Running Tests

```bash
pip install -r requirements_test.txt
pytest tests/ -v
```

## Disclaimer

**THIS IS AN UNOFFICIAL INTEGRATION.**

- This project is NOT affiliated with any electricity distribution company
- The schedule data is sourced from publicly available information and may change without notice
- This integration is provided "as is" without warranty of any kind
- Always verify critical information directly from official sources

## License

MIT License

## Support

If you find this integration useful, please star the repository!
