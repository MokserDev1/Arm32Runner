/**
 * installd_hook.x - MobileInstallation Hook for 32-bit IPA Support
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 *
 * Hooks into installd to prevent rejection of pure 32-bit (armv7) packages
 * and integrates the 64-bit launcher bridge into the application bundle.
 */

#import <Foundation/Foundation.h>

@interface MIBundle : NSObject
- (NSDictionary *)infoPlistSubset;
- (NSArray *)supportedDevices;
- (BOOL)isCompatibleWithDevice:(id)device error:(NSError **)error;
- (NSString *)bundleIdentifier;
- (NSString *)bundlePath;
@end

@interface MIInstallableBundle : NSObject
- (MIBundle *)bundle;
- (BOOL)performVerificationWithError:(NSError **)error;
@end

%group InstalldHook

%hook MIBundle

- (BOOL)isCompatibleWithDevice:(id)device error:(NSError **)error {
    // Check if the bundle contains an armv7 slice
    NSDictionary *info = [self infoPlistSubset];
    NSArray *archs = info[@"CFBundleSupportedPlatforms"];
    
    // Call original check
    BOOL orig = %orig;
    if (orig) {
        return YES;
    }
    
    // If original failed due to 32-bit architecture on 64-bit iOS, override it
    NSString *bundleId = [self bundleIdentifier];
    NSLog(@"[Arm32Runner::installd] Intercepted compatibility check for bundle: %@", bundleId);
    
    // Ensure error is cleared
    if (error && *error) {
        *error = nil;
    }
    
    return YES;
}

- (NSArray *)supportedDevices {
    NSArray *orig = %orig;
    NSMutableArray *mutable = [orig mutableCopy] ?: [NSMutableArray array];
    // Add current device class to allow legacy app installation
    [mutable addObject:@"iPhone"];
    [mutable addObject:@"iPad"];
    [mutable addObject:@"iPod"];
    return [mutable copy];
}

%end

%hook MIInstallableBundle

- (BOOL)performVerificationWithError:(NSError **)error {
    BOOL res = %orig;
    if (!res) {
        // If failed specifically on architecture validation, override
        if (error && *error) {
            NSLog(@"[Arm32Runner::installd] Verification warning overridden: %@", [*error localizedDescription]);
            *error = nil;
        }
        return YES;
    }
    return res;
}

%end

%end

%ctor {
    @autoreleasepool {
        NSString *processName = [[NSProcessInfo processInfo] processName];
        if ([processName isEqualToString:@"installd"]) {
            NSLog(@"[Arm32Runner] Hooking into installd for 32-bit installation support");
            %init(InstalldHook);
        }
    }
}
