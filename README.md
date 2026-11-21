# Arm32Runner: Jailbreak-твик запуска 32-битных IPA для Sileo

**Arm32Runner** — это полноценный jailbreak-твик для пакетного менеджера **Sileo** и современных джейлбрейков (Dopamine, Palera1n, Taurine, unc0ver, Checkra1n), обеспечивающий прозрачный и нативный запуск классических 32-битных приложений iOS (архитектуры ARMv7 и ARMv7s) на 64-битных устройствах.

---

## Архитектура и принципы работы

В отличие от изолированных эмуляторов с собственными виртуальными рабочими столами, **Arm32Runner** полностью интегрируется в подсистемы iOS:

1. **Интеграция с `installd` (`MobileInstallation.framework`):**
   - Перехватывает вызовы валидации совместимости пакета.
   - Позволяет iOS устанавливать чистые 32-битные IPA без ошибки `Application architecture armv7 not supported`.
2. **Интеграция со `SpringBoard`:**
   - Каждое установленное 32-битное приложение получает стандартную иконку на домашнем экране.
   - Запуск происходит штатным тапом по иконке.
   - Автоматически настраивается разрешение экрана и масштабирование под современные экраны Retina / Super Retina OLED.
3. **Мост системных вызовов (`Syscall Translation Bridge`):**
   - Перехватывает 32-битные инструкции `SVC` и транслирует аргументы вызовов в 64-битный формат хостового ядра XNU.
   - Транслирует структуры данных (`stat`, `timeval`, `iovec`, `rlimit`) между 32-битным ABI Darwin и 64-битной хостовой ОС.
4. **Анализатор архитектуры (`arm32-check` CLI):**
   - Утилита для автоматической проверки Mach-O заголовков, слайсов, шифрования FairPlay DRM и зависимостей dyld.

---

## Структура репозитория

```
├── dist/
│   └── com.antigravity.arm32runner_1.0.0_iphoneos-arm64.deb # Готовый deb-пакет для Sileo
├── src/
│   ├── arch_checker/       # Парсер Mach-O и проверка архитектур
│   ├── syscall_bridge/     # Мост трансляции системных вызовов Darwin ABI
│   ├── runtime/            # Загрузчик Mach-O, CPU стейт и UI Bridge
│   └── tweak/              # Хуки Logos для installd и SpringBoard
├── package/
│   ├── DEBIAN/             # Метаданные control, postinst, prerm
│   └── Library/            # Plist фильтры MobileSubstrate
├── tests/                  # Набор автоматических тестов верификации
├── Makefile                # Скрипт сборки Theos
├── scripts/build_deb.py    # Автономный сборщик Debian пакета
├── BUILDING.md             # Инструкция по компиляции
└── COMPATIBILITY.md        # Матрица аппаратной и системной совместимости
```

---

## Установка через Sileo

### Способ 1: Установка готового `.deb` файла
1. Скопируйте файл `dist/com.antigravity.arm32runner_1.0.0_iphoneos-arm64.deb` на устройство (через AirDrop, SSH или Safari).
2. Откройте файл в **Filza File Manager** или поделитесь им в **Sileo**.
3. Нажмите **«Установить»** (Install) в Sileo и подтвердите очередь.
4. После завершения установки произойдет автоматический респринг SpringBoard (`sbreload`).

### Способ 2: Добавление в локальный репозиторий APT
1. Поместите пакет в каталог репозитория: `dpkg-scanpackages . /dev/null > Packages`.
2. Добавьте URL репозитория в Sileo (вкладка «Источники»).
3. Найдите **Arm32Runner** в поиске и установите.

---

## Использование CLI-утилиты проверки `arm32-check`

После установки на устройстве доступна системная консольная команда:

```bash
arm32-check /Applications/OldGame.app/OldGame
```

Пример вывода:
```
================ Mach-O Compatibility Report ================
  Binary Format:      Universal / Fat Binary
  ARMv7 Slice:        YES
  ARMv7s Slice:       NO
  ARM64 Slice:        NO
  FairPlay DRM:       DECRYPTED / CLEAN (cryptid: 0)
  32-bit Slice Size:  1485600 bytes (offset: 0x1000)
  Linked Frameworks (3):
    [01] /System/Library/Frameworks/UIKit.framework/UIKit
    [02] /System/Library/Frameworks/Foundation.framework/Foundation
    [03] /usr/lib/libSystem.B.dylib
-------------------------------------------------------------
  [VERDICT] Pure 32-bit (ARMv7/s). Will execute via Arm32Runner Bridge.
=============================================================
```
