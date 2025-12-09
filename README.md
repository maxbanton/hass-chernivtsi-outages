# Графік відключень електроенергії Чернівецької області

[![CI](https://github.com/maxbanton/ha-cv-power-outages/actions/workflows/ci.yml/badge.svg)](https://github.com/maxbanton/ha-cv-power-outages/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

> ⚠️ **НЕОФІЦІЙНА ІНТЕГРАЦІЯ** - Це громадський проект, який НЕ пов'язаний з енергетичною компанією. Використовуйте на власний ризик.

Інтеграція для Home Assistant, яка показує графік відключень електроенергії для Чернівецької області. Дані отримуються з публічно доступної інформації.

## Можливості

- 📊 **Актуальний графік** - Отримує поточний денний графік відключень
- ⚡ **Сенсор стану** - Показує чи є зараз світло: ON, OFF або MAYBE
- 🔌 **Бінарний сенсор** - Простий індикатор увімк/вимк для автоматизацій
- 📅 **Календар** - Перегляд періодів відключень у календарі Home Assistant
- ⏰ **Час наступної зміни** - Коли буде наступна зміна стану
- 📈 **Залишок годин** - Скільки годин ON/OFF залишилось сьогодні

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

Відвідайте [oblenergo.cv.ua/shutdowns](https://oblenergo.cv.ua/shutdowns/) та натисніть **"ПОШУК ГРУПИ"**:
1. Виберіть дільницю
2. Введіть населений пункт
3. Введіть вулицю
4. Введіть номер будинку

Результати пошуку покажуть номер вашої групи.

## Сутності (Entities)

Для вашої групи інтеграція створює:

| Сутність | Тип | Опис |
|----------|-----|------|
| `sensor.cv_power_state` | Sensor | Поточний стан: `on`, `off`, `maybe` |
| `binary_sensor.cv_power` | Binary Sensor | ON якщо є світло |
| `sensor.cv_next_change` | Sensor | Час наступної зміни стану |
| `sensor.cv_off_hours_remaining` | Sensor | Залишок годин без світла |
| `sensor.cv_on_hours_remaining` | Sensor | Залишок годин зі світлом |
| `sensor.cv_schedule` | Sensor | Повний графік з атрибутами |
| `calendar.cv_outages` | Calendar | Відключення в календарі |

## Стани

| Стан | Опис |
|------|------|
| `on` | Є світло (з) |
| `off` | Немає світла (в) |
| `maybe` | Можливо є світло (мз) |

## ⚠️ Застереження

**ЦЕ НЕОФІЦІЙНА ІНТЕГРАЦІЯ.**

- Цей проект НЕ пов'язаний з енергетичною компанією
- Дані графіку отримуються з публічних джерел і можуть змінюватися
- Інтеграція надається "як є" без гарантій
- Завжди перевіряйте критичну інформацію на офіційних джерелах

---

# Chernivtsi Power Schedule - Home Assistant Integration

[English version]

> ⚠️ **UNOFFICIAL INTEGRATION** - This is a community project and is NOT affiliated with any electricity company. Use at your own risk.

Home Assistant integration for power outage schedule in Chernivtsi region (Чернівецька область), Ukraine.

## Features

- 📊 **Real-time schedule data** - Fetches the current day's power schedule
- ⚡ **Power state sensors** - Shows if electricity is currently ON, OFF, or MAYBE
- 🔌 **Binary sensors** - Simple on/off indicator for automations
- 📅 **Calendar integration** - View outage periods in Home Assistant calendar
- ⏰ **Next change time** - Know when the next power state change will occur
- 📈 **Remaining hours** - See how many ON/OFF hours are left today

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

Visit [oblenergo.cv.ua/shutdowns](https://oblenergo.cv.ua/shutdowns/) and click **"ПОШУК ГРУПИ"** (Search Group) to find your group by address.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.cv_power_state` | Sensor | Current state: `on`, `off`, or `maybe` |
| `binary_sensor.cv_power` | Binary Sensor | ON if power is available |
| `sensor.cv_next_change` | Sensor | Timestamp of next state change |
| `sensor.cv_off_hours_remaining` | Sensor | Remaining OFF hours today |
| `sensor.cv_on_hours_remaining` | Sensor | Remaining ON hours today |
| `sensor.cv_schedule` | Sensor | Full schedule with attributes |
| `calendar.cv_outages` | Calendar | Outage periods as calendar events |

## Power States

| State | Description | Ukrainian |
|-------|-------------|-----------|
| `on` | Electricity is ON | Заживлено (з) |
| `off` | Electricity is OFF | Відключено (в) |
| `maybe` | Possibly ON (gray zone) | Можливо заживлено (мз) |

## Development

### Running Tests

```bash
pip install -r requirements_test.txt
pytest tests/ -v
```

## ⚠️ Disclaimer

**THIS IS AN UNOFFICIAL INTEGRATION.**

- This project is NOT affiliated with any electricity distribution company
- The schedule data is sourced from publicly available information and may change without notice
- This integration is provided "as is" without warranty of any kind
- Always verify critical information directly from official sources

## License

MIT License

## Support

If you find this integration useful, please ⭐ star the repository!
