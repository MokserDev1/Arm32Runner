/**
 * ViewController.h - Main UI View Controller
 * Part of Arm32Runner iOS Application
 */

#import <UIKit/UIKit.h>

@interface ViewController : UIViewController <UIDocumentPickerDelegate>

- (void)handleImportedIPA:(NSURL *)fileURL;

@end
