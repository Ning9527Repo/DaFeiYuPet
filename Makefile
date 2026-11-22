DEBUG = 0
FINALPACKAGE = 1

# Match upstream apelin build: roothide is single-slice arm64e,
# rootless keeps dual-slice FAT (arm64 + arm64e).
ifeq ($(THEOS_PACKAGE_SCHEME),roothide)
ARCHS = arm64e
else
ARCHS = arm64 arm64e
endif

# Share the SDK and deployment targets with the PreferenceBundle.
include MowangDaFeiYuPetBuild.mk
include $(THEOS)/makefiles/common.mk

TWEAK_NAME = MowangDaFeiYuPet
MowangDaFeiYuPet_FILES = $(wildcard Hooks/*.xm Sources/*.m) MowangDaFeiYuPetPrefs/MowangDaFeiYuPetChatController.m
MowangDaFeiYuPet_CFLAGS = -fobjc-arc -I./Headers -I./Sources -IMowangDaFeiYuPetPrefs
MowangDaFeiYuPet_FRAMEWORKS = UIKit Foundation CoreFoundation QuartzCore LocalAuthentication AVFoundation
MowangDaFeiYuPet_LIBRARIES = substrate

include $(THEOS_MAKE_PATH)/tweak.mk

SUBPROJECTS += MowangDaFeiYuPetPrefs
include $(THEOS_MAKE_PATH)/aggregate.mk
