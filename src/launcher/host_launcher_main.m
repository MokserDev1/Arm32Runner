/**
 * host_launcher_main.m - Native 64-bit Host Launcher for Adapted 32-bit Apps
 * Part of Arm32Runner Jailbreak & TrollStore Utility
 *
 * This binary acts as CFBundleExecutable. When SpringBoard launches the app,
 * this binary starts cleanly as a native ARM64 process, sets up the full screen
 * UIWindow, initializes the Arm32Runner execution engine, and runs the 32-bit
 * payload without getting killed by the kernel!
 */

#import <UIKit/UIKit.h>
#include <dlfcn.h>
#include <mach-o/dyld.h>
#include "../syscall_bridge/syscall_bridge.h"
#include "../runtime/macho_loader.h"
#include "../runtime/arm32_core.h"
#include "../runtime/ui_bridge.h"

@interface Arm32AppViewController : UIViewController
@property (nonatomic, strong) UIView *canvasView;
@property (nonatomic, strong) UILabel *badgeLabel;
@end

@implementation Arm32AppViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = [UIColor blackColor];
    
    // Create rendering canvas
    self.canvasView = [[UIView alloc] initWithFrame:self.view.bounds];
    self.canvasView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    [self.view addSubview:self.canvasView];
    
    // Display subtle 32-bit indicator badge
    self.badgeLabel = [[UILabel alloc] initWithFrame:CGRectMake(16, 44, 180, 24)];
    self.badgeLabel.text = @"Arm32Runner: Active";
    self.badgeLabel.textColor = [UIColor colorWithWhite:1.0 alpha:0.4];
    self.badgeLabel.font = [UIFont systemFontOfSize:11 weight:UIFontWeightMedium];
    [self.view addSubview:self.badgeLabel];
    
    // Auto-fade badge after 3 seconds
    [UIView animateWithDuration:1.0 delay:2.0 options:0 animations:^{
        self.badgeLabel.alpha = 0.0;
    } completion:nil];
}

- (BOOL)prefersStatusBarHidden {
    return YES;
}

@end

@interface Arm32AppDelegate : UIResponder <UIApplicationDelegate>
@property (strong, nonatomic) UIWindow *window;
@property (strong, nonatomic) Arm32AppViewController *viewController;
@end

@implementation Arm32AppDelegate

- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {
    self.window = [[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]];
    self.viewController = [[Arm32AppViewController alloc] init];
    self.window.rootViewController = self.viewController;
    [self.window makeKeyAndVisible];
    
    // Start background thread to load and execute the 32-bit payload
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_HIGH, 0), ^{
        [self loadAndExecutePayload];
    });
    
    return YES;
}

- (void)loadAndExecutePayload {
    NSString *bundlePath = [[NSBundle mainBundle] bundlePath];
    NSDictionary *info = [[NSBundle mainBundle] infoDictionary];
    NSString *payloadName = info[@"Arm32PayloadBinary"];
    if (!payloadName) {
        NSString *execName = info[@"CFBundleExecutable"];
        payloadName = [NSString stringWithFormat:@"%@.arm32", execName];
    }
    
    NSString *payloadPath = [bundlePath stringByAppendingPathComponent:payloadName];
    NSLog(@"[Arm32Runner] Loading 32-bit payload from: %@", payloadPath);
    
    if (![[NSFileManager defaultManager] fileExistsAtPath:payloadPath]) {
        NSLog(@"[Arm32Runner::Error] 32-bit payload not found at %@", payloadPath);
        return;
    }
    
    // Initialize Mach-O Loader and execute payload
    MachOAnalysisResult analysis;
    if (analyze_macho_file([payloadPath UTF8String], &analysis)) {
        LoadedAppImage image;
        if (macho_loader_init(&image, 128 * 1024 * 1024)) {
            if (macho_loader_load(&image, [payloadPath UTF8String], &analysis)) {
                SyscallBridgeContext bridge;
                syscall_bridge_init(&bridge, image.virtual_memory, image.memory_size);
                
                Arm32Cpu cpu;
                if (arm32_cpu_init(&cpu, &image, &bridge)) {
                    NSLog(@"[Arm32Runner] Payload mapped and executing starting at PC: 0x%X", image.entry_point);
                    arm32_cpu_run(&cpu, 0);
                }
            }
        }
    }
}

@end

int main(int argc, char * argv[]) {
    @autoreleasepool {
        return UIApplicationMain(argc, argv, nil, NSStringFromClass([Arm32AppDelegate class]));
    }
}
