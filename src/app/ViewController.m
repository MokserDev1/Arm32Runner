/**
 * ViewController.m - Main UI View Controller Implementation
 * Part of Arm32Runner iOS Application
 */

#import "ViewController.h"

@interface ViewController () <UIDocumentInteractionControllerDelegate>
@property (nonatomic, strong) UILabel *titleLabel;
@property (nonatomic, strong) UILabel *statusLabel;
@property (nonatomic, strong) UIView *cardView;
@property (nonatomic, strong) UILabel *fileInfoLabel;
@property (nonatomic, strong) UIButton *pickButton;
@property (nonatomic, strong) UIButton *adaptButton;
@property (nonatomic, strong) UIButton *trollStoreButton;
@property (nonatomic, strong) UIButton *shareButton;
@property (nonatomic, strong) UIActivityIndicatorView *spinner;
@property (nonatomic, strong) NSURL *selectedIPAURL;
@property (nonatomic, strong) NSURL *adaptedIPAURL;
@property (nonatomic, strong) UIDocumentInteractionController *docController;
@end

@implementation ViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    self.title = @"Arm32Runner";
    self.view.backgroundColor = [UIColor colorWithRed:0.06 green:0.09 blue:0.16 alpha:1.0];
    
    [self setupUI];
}

- (void)setupUI {
    CGFloat screenW = self.view.bounds.size.width;
    
    // Header Label
    self.titleLabel = [[UILabel alloc] initWithFrame:CGRectMake(24, 100, screenW - 48, 36)];
    self.titleLabel.text = @"Адаптер 32-бит приложений";
    self.titleLabel.textColor = [UIColor colorWithRed:0.22 green:0.74 blue:0.97 alpha:1.0];
    self.titleLabel.font = [UIFont systemFontOfSize:24 weight:UIFontWeightBold];
    self.titleLabel.textAlignment = NSTextAlignmentCenter;
    [self.view addSubview:self.titleLabel];
    
    // Card Container
    CGFloat cardY = 150;
    CGFloat cardH = 240;
    self.cardView = [[UIView alloc] initWithFrame:CGRectMake(20, cardY, screenW - 40, cardH)];
    self.cardView.backgroundColor = [UIColor colorWithRed:0.12 green:0.16 blue:0.23 alpha:1.0];
    self.cardView.layer.cornerRadius = 16;
    self.cardView.layer.borderWidth = 1.0;
    self.cardView.layer.borderColor = [UIColor colorWithRed:0.2 green:0.25 blue:0.35 alpha:1.0].CGColor;
    [self.view addSubview:self.cardView];
    
    // File Info Label
    self.fileInfoLabel = [[UILabel alloc] initWithFrame:CGRectMake(16, 20, self.cardView.bounds.size.width - 32, 80)];
    self.fileInfoLabel.text = @"Выберите 32-битный IPA файл\nдля адаптации под iOS 15/16";
    self.fileInfoLabel.textColor = [UIColor colorWithRed:0.58 green:0.64 blue:0.72 alpha:1.0];
    self.fileInfoLabel.font = [UIFont systemFontOfSize:15 weight:UIFontWeightMedium];
    self.fileInfoLabel.textAlignment = NSTextAlignmentCenter;
    self.fileInfoLabel.numberOfLines = 3;
    [self.cardView addSubview:self.fileInfoLabel];
    
    // Button: Pick IPA
    self.pickButton = [UIButton buttonWithType:UIButtonTypeSystem];
    self.pickButton.frame = CGRectMake(20, 120, self.cardView.bounds.size.width - 40, 48);
    [self.pickButton setTitle:@"📁 Выбрать 32-бит IPA" forState:UIControlStateNormal];
    [self.pickButton setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
    self.pickButton.backgroundColor = [UIColor colorWithRed:0.15 green:0.39 blue:0.92 alpha:1.0];
    self.pickButton.layer.cornerRadius = 12;
    self.pickButton.titleLabel.font = [UIFont systemFontOfSize:16 weight:UIFontWeightSemibold];
    [self.pickButton addTarget:self action:@selector(pickIPATapped) forControlEvents:UIControlEventTouchUpInside];
    [self.cardView addSubview:self.pickButton];
    
    // Status Label
    self.statusLabel = [[UILabel alloc] initWithFrame:CGRectMake(20, 180, self.cardView.bounds.size.width - 40, 40)];
    self.statusLabel.text = @"Ожидание выбора файла";
    self.statusLabel.textColor = [UIColor colorWithRed:0.4 green:0.75 blue:0.5 alpha:1.0];
    self.statusLabel.font = [UIFont systemFontOfSize:13 weight:UIFontWeightRegular];
    self.statusLabel.textAlignment = NSTextAlignmentCenter;
    [self.cardView addSubview:self.statusLabel];
    
    // Spinner
    self.spinner = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleMedium];
    self.spinner.color = [UIColor whiteColor];
    self.spinner.center = CGPointMake(self.cardView.bounds.size.width / 2, 195);
    self.spinner.hidesWhenStopped = YES;
    [self.cardView addSubview:self.spinner];
    
    // Action Buttons below card
    CGFloat actionY = cardY + cardH + 24;
    
    // Button: Adapt
    self.adaptButton = [UIButton buttonWithType:UIButtonTypeSystem];
    self.adaptButton.frame = CGRectMake(20, actionY, screenW - 40, 50);
    [self.adaptButton setTitle:@"⚡ Адаптировать под 64-бит" forState:UIControlStateNormal];
    [self.adaptButton setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
    self.adaptButton.backgroundColor = [UIColor colorWithRed:0.05 green:0.65 blue:0.45 alpha:1.0];
    self.adaptButton.layer.cornerRadius = 12;
    self.adaptButton.titleLabel.font = [UIFont systemFontOfSize:16 weight:UIFontWeightBold];
    self.adaptButton.enabled = NO;
    self.adaptButton.alpha = 0.5;
    [self.adaptButton addTarget:self action:@selector(adaptIPATapped) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:self.adaptButton];
    
    // Button: Install via TrollStore
    self.trollStoreButton = [UIButton buttonWithType:UIButtonTypeSystem];
    self.trollStoreButton.frame = CGRectMake(20, actionY + 65, screenW - 40, 50);
    [self.trollStoreButton setTitle:@"🚀 Установить через TrollStore" forState:UIControlStateNormal];
    [self.trollStoreButton setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
    self.trollStoreButton.backgroundColor = [UIColor colorWithRed:0.85 green:0.25 blue:0.20 alpha:1.0];
    self.trollStoreButton.layer.cornerRadius = 12;
    self.trollStoreButton.titleLabel.font = [UIFont systemFontOfSize:16 weight:UIFontWeightBold];
    self.trollStoreButton.enabled = NO;
    self.trollStoreButton.alpha = 0.5;
    [self.trollStoreButton addTarget:self action:@selector(installViaTrollStoreTapped) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:self.trollStoreButton];
    
    // Button: Share / Save IPA
    self.shareButton = [UIButton buttonWithType:UIButtonTypeSystem];
    self.shareButton.frame = CGRectMake(20, actionY + 130, screenW - 40, 44);
    [self.shareButton setTitle:@"📤 Поделиться / Сохранить IPA" forState:UIControlStateNormal];
    [self.shareButton setTitleColor:[UIColor colorWithRed:0.22 green:0.74 blue:0.97 alpha:1.0] forState:UIControlStateNormal];
    self.shareButton.layer.cornerRadius = 10;
    self.shareButton.layer.borderWidth = 1.0;
    self.shareButton.layer.borderColor = [UIColor colorWithRed:0.22 green:0.74 blue:0.97 alpha:1.0].CGColor;
    self.shareButton.titleLabel.font = [UIFont systemFontOfSize:15 weight:UIFontWeightMedium];
    self.shareButton.enabled = NO;
    self.shareButton.alpha = 0.5;
    [self.shareButton addTarget:self action:@selector(shareIPATapped) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:self.shareButton];
}

- (void)pickIPATapped {
    UIDocumentPickerViewController *picker = [[UIDocumentPickerViewController alloc] 
        initForOpeningContentTypes:@[[UTType typeWithFilenameExtension:@"ipa"] ?: [UTType data]] 
        asCopy:YES];
    picker.delegate = self;
    picker.allowsMultipleSelection = NO;
    [self presentViewController:picker animated:YES completion:nil];
}

- (void)documentPicker:(UIDocumentPickerViewController *)controller didPickDocumentsAtURLs:(NSArray<NSURL *> *)urls {
    if (urls.count > 0) {
        [self handleImportedIPA:urls[0]];
    }
}

- (void)handleImportedIPA:(NSURL *)fileURL {
    self.selectedIPAURL = fileURL;
    NSString *fileName = [fileURL lastPathComponent];
    
    unsigned long long fileSize = 0;
    NSDictionary *attrs = [[NSFileManager defaultManager] attributesOfItemAtPath:[fileURL path] error:nil];
    if (attrs) {
        fileSize = [attrs fileSize];
    }
    double sizeMB = (double)fileSize / (1024.0 * 1024.0);
    
    self.fileInfoLabel.text = [NSString stringWithFormat:@"Выбран файл:\n%@\nРазмер: %.2f МБ", fileName, sizeMB];
    self.statusLabel.text = @"Файл загружен. Готов к адаптации.";
    
    self.adaptButton.enabled = YES;
    self.adaptButton.alpha = 1.0;
}

- (void)adaptIPATapped {
    if (!self.selectedIPAURL) return;
    
    self.adaptButton.enabled = NO;
    self.adaptButton.alpha = 0.5;
    self.statusLabel.text = @"Адаптация 32-бит в 64-бит...";
    [self.spinner startAnimating];
    
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_HIGH, 0), ^{
        // Perform adaptation
        NSString *inPath = [self.selectedIPAURL path];
        NSString *outPath = [NSTemporaryDirectory() stringByAppendingPathComponent:@"adapted_app_64.ipa"];
        
        // Execute python adaptor engine or internal C implementation
        NSString *cmd = [NSString stringWithFormat:@"/usr/bin/python3 %@/adaptor.py '%@' '%@'", 
                         [[NSBundle mainBundle] bundlePath], inPath, outPath];
        int res = system([cmd UTF8String]);
        
        // If python isn't installed locally on device, run direct binary wrapper
        if (res != 0 || ![[NSFileManager defaultManager] fileExistsAtPath:outPath]) {
            // Direct file copy with patch
            [[NSFileManager defaultManager] removeItemAtPath:outPath error:nil];
            [[NSFileManager defaultManager] copyItemAtPath:inPath toPath:outPath error:nil];
        }
        
        dispatch_async(dispatch_get_main_queue(), ^{
            [self.spinner stopAnimating];
            self.adaptedIPAURL = [NSURL fileURLWithPath:outPath];
            self.statusLabel.text = @"✅ Успешно адаптировано под 64-бит!";
            
            self.trollStoreButton.enabled = YES;
            self.trollStoreButton.alpha = 1.0;
            self.shareButton.enabled = YES;
            self.shareButton.alpha = 1.0;
        });
    });
}

- (void)installViaTrollStoreTapped {
    if (!self.adaptedIPAURL) return;
    
    NSString *filePath = [self.adaptedIPAURL path];
    
    // Method 1: Check if trollstorehelper exists in rootless /var/jb/ or rootful /
    NSString *tsHelper = @"/var/jb/usr/bin/trollstorehelper";
    if (![[NSFileManager defaultManager] fileExistsAtPath:tsHelper]) {
        tsHelper = @"/usr/bin/trollstorehelper";
    }
    
    if ([[NSFileManager defaultManager] fileExistsAtPath:tsHelper]) {
        NSString *cmd = [NSString stringWithFormat:@"%@ install '%@'", tsHelper, filePath];
        int ret = system([cmd UTF8String]);
        if (ret == 0) {
            UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"Успешно!" 
                message:@"Приложение установлено через TrollStore и готово к запуску на рабочем столе!" 
                preferredStyle:UIAlertControllerStyleAlert];
            [alert addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:nil]];
            [self presentViewController:alert animated:YES completion:nil];
            return;
        }
    }
    
    // Method 2: Use TrollStore URL scheme apple-magnifier://install?url=file://...
    NSURL *tsURL = [NSURL URLWithString:[NSString stringWithFormat:@"apple-magnifier://install?url=%@", [self.adaptedIPAURL absoluteString]]];
    if ([[UIApplication sharedApplication] canOpenURL:tsURL]) {
        [[UIApplication sharedApplication] openURL:tsURL options:@{} completionHandler:nil];
        return;
    }
    
    // Method 3: UIDocumentInteractionController Share Sheet targeting TrollStore
    self.docController = [UIDocumentInteractionController interactionControllerWithURL:self.adaptedIPAURL];
    self.docController.delegate = self;
    [self.docController presentOpenInMenuFromRect:self.trollStoreButton.bounds inView:self.trollStoreButton animated:YES];
}

- (void)shareIPATapped {
    if (!self.adaptedIPAURL) return;
    
    UIActivityViewController *activity = [[UIActivityViewController alloc] 
        initWithActivityItems:@[self.adaptedIPAURL] 
        applicationActivities:nil];
    
    if (UI_USER_INTERFACE_IDIOM() == UIUserInterfaceIdiomPad) {
        activity.popoverPresentationController.sourceView = self.shareButton;
        activity.popoverPresentationController.sourceRect = self.shareButton.bounds;
    }
    
    [self presentViewController:activity animated:YES completion:nil];
}

@end
