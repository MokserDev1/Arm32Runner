/**
 * springboard_hook.x - SpringBoard & Process Launch Integration Hook
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 *
 * Hooks into SpringBoard to manage seamless app launching, icon representation,
 * and display scaling without any auxiliary emulator launchers.
 */

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

@interface SBApplication : NSObject
- (NSString *)bundleIdentifier;
- (NSString *)displayName;
- (BOOL)isClassic;
@end

@interface SBApplicationController : NSObject
+ (instancetype)sharedInstance;
- (SBApplication *)applicationWithBundleIdentifier:(NSString *)bundleIdentifier;
@end

%group SpringBoardHook

%hook SBApplication

- (BOOL)isClassic {
    // Report classic app when running 32-bit ARMv7 apps to enable proper frame scaling
    NSString *bundleId = [self bundleIdentifier];
    if ([bundleId hasPrefix:@"com.legacy."] || [bundleId containsString:@".arm32."]) {
        return YES;
    }
    return %orig;
}

%end

%hook SBApplicationController

- (void)_appVisibilityChanged:(id)arg1 {
    %orig;
}

%end

%end

%ctor {
    @autoreleasepool {
        NSString *processName = [[NSProcessInfo processInfo] processName];
        if ([processName isEqualToString:@"SpringBoard"]) {
            NSLog(@"[Arm32Runner] SpringBoard hook active. Seamless 32-bit app launching enabled.");
            %init(SpringBoardHook);
        }
    }
}
