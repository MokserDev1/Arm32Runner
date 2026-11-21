/**
 * AppDelegate.m - Application Delegate Implementation
 * Part of Arm32Runner iOS Application
 */

#import "AppDelegate.h"
#import "ViewController.h"

@implementation AppDelegate

- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {
    self.window = [[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]];
    self.window.backgroundColor = [UIColor colorWithRed:0.04 green:0.06 blue:0.10 alpha:1.0];
    
    ViewController *vc = [[ViewController alloc] init];
    UINavigationController *nav = [[UINavigationController alloc] initWithRootViewController:vc];
    
    // Style navigation bar for dark theme
    nav.navigationBar.barStyle = UIBarStyleBlack;
    nav.navigationBar.translucent = YES;
    nav.navigationBar.tintColor = [UIColor colorWithRed:0.22 green:0.74 blue:0.97 alpha:1.0];
    
    self.window.rootViewController = nav;
    [self.window makeKeyAndVisible];
    return YES;
}

- (BOOL)application:(UIApplication *)app openURL:(NSURL *)url options:(NSDictionary<UIApplicationOpenURLOptionsKey,id> *)options {
    // Handle opening IPA files from other apps (AirDrop, Files, Safari)
    if ([url isFileURL] && [[url pathExtension] isEqualToString:@"ipa"]) {
        UINavigationController *nav = (UINavigationController *)self.window.rootViewController;
        if ([nav.topViewController isKindOfClass:[ViewController class]]) {
            [(ViewController *)nav.topViewController handleImportedIPA:url];
        }
        return YES;
    }
    return NO;
}

@end
