/**
 * Tweak.x - Main Entry Point for Arm32Runner Substrate / ElleKit Extension
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#import <Foundation/Foundation.h>

%ctor {
    @autoreleasepool {
        NSLog(@"[Arm32Runner] Core tweak loaded successfully into process: %@", 
              [[NSProcessInfo processInfo] processName]);
    }
}
