# Инструкция по сборке Arm32Runner

Проект поддерживает два способа сборки:
1. **Автономная сборка без Theos (Python + GCC):** Создает готовый `.deb` пакет для Sileo на любой платформе (Windows, Linux, macOS).
2. **Сборка через Theos (для iOS-разработчиков):** Для компиляции в окружении macOS / Linux с установленным iOS Toolchain.

---

## Способ 1: Автономная сборка пакета (.deb)

Этот метод не требует наличия установленного Theos и собирает готовый deb-пакет:

```bash
# 1. Запуск автоматических тестов и верификации
python tests/run_all_tests.py

# 2. Прямая сборка пакета
python scripts/build_deb.py
```

Готовый пакет будет создан по пути:
`dist/com.antigravity.arm32runner_1.0.0_iphoneos-arm64.deb`

---

## Способ 2: Сборка через Theos

Если вы ведете разработку на macOS или в Linux с установленным Theos:

### 1. Настройка переменных окружения
```bash
export THEOS=/opt/theos
export THEOS_DEVICE_IP=192.168.1.100 # IP адрес вашего iPhone
```

### 2. Сборка для классического джейлбрейка (Rootful, iOS 12 - 14)
```bash
make clean
make package FINALPACKAGE=1
```

### 3. Сборка для современного джейлбрейка (Rootless, iOS 15 - 16, Dopamine / Palera1n)
```bash
make clean
make package FINALPACKAGE=1 THEOS_PACKAGE_SCHEME=rootless
```

### 4. Прямая установка на подключенное устройство
```bash
make do
```
Команда соберет проект, передаст `.deb` на устройство по SSH и вызовет `sbreload`.
