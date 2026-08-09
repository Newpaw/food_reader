function normalizeBaseUrl(value) {
  return value ? value.replace(/\/+$/, '') : '';
}

const APP_STORAGE_PREFIX = 'food-reader';
const SUPPORTED_LOCALES = ['en', 'cs'];
const DEFAULT_LOCALE =
  typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('cs') ? 'cs' : 'en';

let currentUserContext = null;
let currentLocale =
  typeof window !== 'undefined'
    ? window.localStorage.getItem(`${APP_STORAGE_PREFIX}:locale`) || DEFAULT_LOCALE
    : DEFAULT_LOCALE;

const TRANSLATIONS = {
  en: {
    'title.login': 'Food Reader | Sign In',
    'title.add': 'Food Reader | Add Meal',
    'title.history': 'Food Reader | History',
    'title.metrics': 'Food Reader | Metrics',
    'title.profile': 'Food Reader | Profile',
    'brand.name': 'Food Reader',
    'brand.tagline': 'mobile nutrition log',
    'nav.add': 'Add Meal',
    'nav.addShort': 'Add',
    'nav.history': 'History',
    'nav.metrics': 'Metrics',
    'nav.profile': 'Profile',
    'button.install': 'Install',
    'button.installApp': 'Install app',
    'button.notNow': 'Not now',
    'button.showSteps': 'Show steps',
    'button.logout': 'Log out',
    'button.takePhoto': 'Take photo',
    'button.useSavedPhoto': 'Choose from gallery',
    'button.choosePhoto': 'Choose photo',
    'button.analyzePhoto': 'Analyze meal',
    'button.analyzeText': 'Analyze meal text',
    'button.applyRange': 'Apply range',
    'button.refreshMetrics': 'Refresh metrics',
    'button.saveProfile': 'Save profile',
    'button.resetForm': 'Reset form',
    'button.connectWithings': 'Connect Withings',
    'button.syncWithings': 'Sync Withings',
    'button.disconnectWithings': 'Disconnect',
    'button.saveChanges': 'Save changes',
    'button.reset': 'Reset',
    'button.rerunAnalysis': 'Re-run analysis',
    'button.openHistory': 'Open history',
    'button.signIn': 'Sign in',
    'button.createAccount': 'Create account',
    'button.close': 'Close',
    'button.review': 'Review',
    'button.logAgain': 'Log again',
    'button.remove': 'Remove',
    'button.saveFavorite': 'Save as favorite',
    'button.editMeal': 'Edit meal',
    'button.addAnotherMeal': 'Add another meal',
    'button.cancelEdit': 'Cancel edit',
    'button.startVoice': 'Start voice input',
    'button.stopVoice': 'Stop listening',
    'button.syncQueue': 'Sync queue',
    'button.improveEstimate': 'Improve estimate',
    'button.applyRefinement': 'Update estimate',
    'button.openEdit': 'Edit meal',
    'button.editMeal': 'Edit meal',
    'button.saveMeal': 'Save meal',
    'button.view': 'View',
    'button.delete': 'Delete',
    'button.today': 'Today',
    'button.last7': 'Last 7 days',
    'button.last30': 'Last 30 days',
    'button.last90': 'Last 90 days',
    'button.customDates': 'Custom dates',
    'filter.activeRange': 'Active range',
    'label.email': 'Email',
    'label.password': 'Password',
    'label.name': 'Name',
    'label.describeMeal': 'Describe the meal',
    'text.placeholder': 'Example: chicken shawarma bowl with rice, pickles, tahini, and cucumber salad',
    'label.notes': 'Notes',
    'label.mealType': 'Meal type',
    'label.consumedAt': 'Consumed at',
    'label.calories': 'Calories',
    'label.protein': 'Protein (g)',
    'label.fat': 'Fat (g)',
    'label.carbs': 'Carbs (g)',
    'label.fiber': 'Fiber (g)',
    'label.sugar': 'Sugar (g)',
    'label.sodium': 'Sodium (mg)',
    'label.from': 'From',
    'label.to': 'To',
    'label.height': 'Height (cm)',
    'label.weight': 'Weight (kg)',
    'label.age': 'Age',
    'label.gender': 'Gender',
    'label.activity': 'Activity level',
    'label.goal': 'Goal',
    'label.diet': 'Diet preference',
    'label.customCalories': 'Custom calories',
    'label.customProtein': 'Custom protein',
    'label.customCarbs': 'Custom carbs',
    'label.customFat': 'Custom fat',
    'label.customFiber': 'Custom fiber',
    'label.language': 'Language',
    'install.promptFallback': 'Use your browser menu to install this app if the prompt is not available.',
    'install.bannerEyebrow': 'Install app',
    'install.bannerTitle': 'Keep Food Reader one tap away',
    'install.bannerBody': 'Install the app for faster launch, full-screen meal logging, and better offline access.',
    'install.fallbackTitle': 'Add Food Reader to your Home Screen',
    'install.fallbackBody': 'On this device, use your browser menu to add the app so meal capture stays one tap away.',
    'install.dismissed': 'Install prompt dismissed for now.',
    'install.installed': 'Food Reader is installed and ready.',
    'install.iosStep1': 'Tap the Share button in Safari.',
    'install.iosStep2': 'Choose Add to Home Screen.',
    'install.iosStep3': 'Confirm Add to place Food Reader on your device.',
    'install.instructionsTitle': 'Install Food Reader',
    'install.instructionsBody': 'Save the app to your Home Screen for faster meal logging and a cleaner full-screen experience.',
    'install.instructionsHint': 'You only need to do this once.',
    'option.breakfast': 'Breakfast',
    'option.lunch': 'Lunch',
    'option.dinner': 'Dinner',
    'option.snack': 'Snack',
    'option.choose': 'Choose',
    'option.male': 'Male',
    'option.female': 'Female',
    'option.other': 'Other',
    'option.sedentary': 'Sedentary',
    'option.lightly_active': 'Lightly active',
    'option.moderately_active': 'Moderately active',
    'option.very_active': 'Very active',
    'option.extremely_active': 'Extremely active',
    'option.weight_loss': 'Weight loss',
    'option.maintenance': 'Maintenance',
    'option.muscle_gain': 'Muscle gain',
    'option.none': 'Balanced',
    'option.high_protein': 'High protein',
    'option.low_carb': 'Low carb',
    'option.keto': 'Keto',
    'option.vegetarian': 'Vegetarian',
    'option.vegan': 'Vegan',
    'login.welcomeBack': 'Welcome back',
    'login.signInHeading': 'Sign in',
    'login.signInSupport': 'Use your saved account to continue quickly.',
    'login.newAccount': 'New account',
    'login.createAccess': 'Create access',
    'login.createSupport': 'Create an account to save meals and keep your history.',
    'login.newHere': 'New here?',
    'login.haveAccount': 'Already have an account?',
    'login.signingIn': 'Signing you in...',
    'login.registering': 'Creating your account...',
    'login.registered': 'Account created. You can sign in now.',
    'home.heroEyebrow': 'Capture fast, correct later',
    'home.heroTitle': 'Log meals in seconds without losing control of the numbers.',
    'home.heroBody': 'Use a photo when you want speed, type the meal when a camera is inconvenient, scan packaged food, or reuse saved templates. Every entry still opens into a review panel.',
    'home.todayEyebrow': 'Today',
    'home.todayHeading': 'Daily dashboard',
    'home.templatesEyebrow': 'Quick reuse',
    'home.templatesHeading': 'Favorites and templates',
    'home.captureEyebrow': 'New entry',
    'home.captureHeading': 'Add a meal',
    'home.capturePhoto': 'Photo',
    'home.captureText': 'Text',
    'home.captureModeHelper': 'Choose one input method for the same meal. Photo uses image analysis, text is a full manual alternative.',
    'home.mobileCameraHint': 'Open the camera directly on your phone, then review the estimate before saving.',
    'home.uploadHint': 'Take or upload a meal photo',
    'home.analysisContextLabel': 'Add details for better analysis',
    'home.analysisContextHelper': 'You can add ingredients, portion details, sauces, drinks, or anything not clearly visible in the photo.',
    'home.analysisContextPlaceholder': 'Example: double cheeseburger, only half the fries eaten, drink was zero sugar',
    'home.analysisLoadingEyebrow': 'Analysis in progress',
    'home.analysisLoadingTitle': 'Analyzing your meal',
    'home.analysisLoadingBody': 'This can take a few seconds.',
    'home.analysisLoadingLongWait': 'Still working. Complex meals can take a few extra seconds.',
    'home.voiceHint': 'Dictate a meal and then review the estimate before saving.',
    'home.recentEyebrow': 'Keep moving',
    'home.recentHeading': 'Recent meals',
    'home.reviewEyebrow': 'Review',
    'home.reviewHeading': 'Adjust the nutrition draft',
    'home.latestEntry': 'Latest entry',
    'home.moreDetailsHeading': 'More nutrition details',
    'home.moreDetailsHint': 'Fiber, sugar, sodium, and meal context',
    'home.correctionHeading': 'Correct the AI identification',
    'home.correctionPlaceholder': 'Example: this was grilled pork, not chicken',
    'home.refineHeading': 'Add missing details',
    'home.refineHelper': 'Clarify portion size, hidden ingredients, sauces, drinks, or what you did not eat.',
    'home.refinePlaceholder': 'Example: this was a double burger, I only ate half the fries, and there was mayo under the bun',
    'home.insightHighProteinTitle': 'High-protein meal',
    'home.insightHighProteinBody': 'Protein carries a strong share of this estimate, so it should keep you fuller than a lighter snack.',
    'home.insightHighFiberTitle': 'Fiber-supportive meal',
    'home.insightHighFiberBody': 'Fiber stands out here, which usually makes the meal feel steadier than fast calories alone.',
    'home.insightRichTitle': 'Rich, calorie-dense meal',
    'home.insightRichBody': 'Calories are likely being pushed up by the combination of fat and carbs.',
    'home.insightBalancedTitle': 'Balanced estimate',
    'home.insightBalancedBody': 'This looks like a moderate meal without one macro overwhelmingly dominating the total.',
    'home.templatesEmpty': 'Save a reviewed meal and it will appear here for one-tap logging.',
    'home.queueEmpty': 'Nothing is waiting to sync.',
    'home.queueHeading': 'Offline capture queue',
    'home.queueReady': 'Everything is synced.',
    'home.queueCompact': '{count} entries waiting to sync',
    'home.queueKind.photo': 'Photo',
    'home.queueKind.text': 'Text entry',
    'home.dashboardTargetsMissing': 'Create a profile to compare today against a calorie target.',
    'home.dashboardInsights': 'Today you logged {meals} meals and {calories} kcal.',
    'home.dashboardRemaining': '{remaining} kcal remaining',
    'home.dashboardOver': '{remaining} kcal above target',
    'home.dashboardStreak': '{days}-day logging streak',
    'home.dashboardTemplates': '{count} saved templates',
    'home.dashboardQueue': '{count} pending uploads',
    'home.dashboardProtein': 'Protein today',
    'home.dashboardFiber': 'Fiber today',
    'home.dashboardCalories': 'Calories today',
    'home.dashboardTarget': 'Target',
    'home.templateSaved': 'Template saved for quick reuse.',
    'home.voiceUnsupported': 'Voice input is not supported in this browser.',
    'home.voiceActive': 'Listening... speak naturally.',
    'home.voiceStopped': 'Voice input stopped.',
    'home.queueAddedText': 'Offline. The meal was added to the sync queue.',
    'home.queueAddedPhoto': 'Offline. The photo was saved to the sync queue.',
    'home.queueSyncing': 'Syncing queued meals...',
    'home.queueSynced': 'Queued meals synced.',
    'home.queueSyncError': 'Some queued meals still need a connection.',
    'home.photoRequired': 'Choose a photo before submitting.',
    'home.photoPreparing': 'Preparing your photo...',
    'home.loadingStageUpload': 'Checking the photo and preparing the image.',
    'home.loadingStageDetect': 'Reviewing ingredients and portion size.',
    'home.loadingStageEstimate': 'Estimating calories and macros.',
    'home.loadingStageTextRead': 'Reviewing the meal description.',
    'home.loadingStageReview': 'Building your review card.',
    'home.textRequired': 'Describe the meal before submitting.',
    'home.photoAnalyzing': 'Analyzing your meal photo...',
    'home.textAnalyzing': 'Analyzing your meal description...',
    'home.mealAdded': 'Meal added. Review the estimate below.',
    'home.savingAdjustments': 'Saving adjustments...',
    'home.mealUpdated': 'Meal updated.',
    'home.mealDeleted': 'Meal deleted.',
    'home.deleteConfirm': 'Delete this meal permanently?',
    'home.resetDone': 'Changes reset.',
    'home.correctionRequired': 'Add more detail before updating the estimate.',
    'home.refineCancelled': 'Estimate refinement cancelled.',
    'home.reanalyzing': 'Reanalyzing meal...',
    'home.reanalysisUpdated': 'AI analysis updated.',
    'home.noMeals': 'No meals yet. Add one to get started.',
    'history.heroEyebrow': 'History',
    'history.heroTitle': 'Review the full log, grouped in a way that still works on a phone.',
    'history.heroBody': 'Filter a date range, spot outliers quickly, and adjust entries without leaving the history screen.',
    'history.filterEyebrow': 'Range',
    'history.filterHeading': 'Filter history',
    'history.templatesEyebrow': 'Reuse',
    'history.templatesHeading': 'Saved templates',
    'history.summary.totalMeals': 'Total meals',
    'history.summary.totalCalories': 'Total calories',
    'history.summary.avgPerMeal': 'Avg per meal',
    'history.mealsLabel': 'meals',
    'history.empty': 'No meals matched this range.',
    'history.noNotes': 'No notes yet.',
    'history.loading': 'Loading meal history...',
    'history.deleted': 'Meal deleted.',
    'history.deleting': 'Deleting meal...',
    'history.saving': 'Saving changes...',
    'history.saved': 'Meal updated.',
    'history.deleteConfirm': 'Delete this meal permanently?',
    'metrics.heroEyebrow': 'Metrics',
    'metrics.heroTitle': 'See whether your daily pattern is moving toward the target.',
    'metrics.heroBody': 'The dashboard stays readable on narrow screens, but expands into a denser command view on larger layouts.',
    'metrics.loading': 'Loading metrics...',
    'metrics.todayEyebrow': 'Today',
    'metrics.todayHeading': 'Daily goal status',
    'metrics.todayOnTrack': 'On track today',
    'metrics.todayOverGoal': 'Over goal today',
    'metrics.todayNoMeals': 'No meals logged yet today.',
    'metrics.todayNoTarget': 'Set a profile target to judge today properly.',
    'metrics.todayConsumed': '{calories} of {target} kcal',
    'metrics.todayNoTargetConsumed': '{calories} kcal logged today',
    'metrics.todayRemaining': '{remaining} kcal remaining today',
    'metrics.todayOverAmount': '{remaining} kcal over target',
    'metrics.todayMeals': 'Meals today',
    'metrics.todayProtein': 'Protein today',
    'metrics.todayCarbs': 'Carbs today',
    'metrics.todayFat': 'Fat today',
    'metrics.todayFiber': 'Fiber today',
    'metrics.adaptiveTarget': 'Adaptive activity target',
    'metrics.adaptiveTargetDetail': 'Today’s target is refined from your completed Oura activity days.',
    'metrics.filterNote': 'This filter controls everything below. The today card above always shows today only.',
    'metrics.filterEyebrow': 'Range',
    'metrics.filterHeading': 'Filter analysis',
    'metrics.avgPerDay': 'avg/day',
    'metrics.rangeEyebrow': 'Selected range',
    'metrics.rangeHeading': 'Range summary',
    'metrics.targetsEyebrow': 'Goal setup',
    'metrics.targetsHeading': 'Current targets',
    'metrics.avgDailyCalories': 'Avg daily calories',
    'metrics.totalCalories': 'Total calories',
    'metrics.totalMeals': 'Total meals',
    'metrics.fiberLogged': 'Fiber logged',
    'metrics.calories': 'Calories',
    'metrics.protein': 'Protein',
    'metrics.carbs': 'Carbs',
    'metrics.fat': 'Fat',
    'metrics.fiber': 'Fiber',
    'metrics.mealsLabel': 'meals',
    'metrics.macroKcal': 'macro kcal',
    'metrics.noMacroData': 'Macro distribution will appear after you log meals.',
    'metrics.progressEyebrow': 'Progress',
    'metrics.progressHeading': 'Average intake versus target',
    'metrics.dailyEyebrow': 'Daily calories',
    'metrics.dailyHeading': 'Bar view',
    'metrics.macroEyebrow': 'Macro balance',
    'metrics.macroHeading': 'Distribution',
    'metrics.dayByDayEyebrow': 'Day by day',
    'metrics.dayByDayHeading': 'Summary list',
    'metrics.targetsMissing': 'Create a profile to unlock personalized calorie and macro targets.',
    'metrics.setupProfile': 'Set up profile',
    'metrics.dayListEmpty': 'Daily breakdown will appear after you log meals.',
    'metrics.bodyEyebrow': 'Body metrics',
    'metrics.bodyHeading': 'Withings weight trend',
    'metrics.bodyEmpty': 'Connect Withings and sync your scale to see body metrics here.',
    'metrics.latestWeight': 'Latest weight',
    'metrics.weightChange': 'Weight change',
    'metrics.bodyFat': 'Body fat',
    'metrics.muscleMass': 'Muscle mass',
    'metrics.measurements': 'measurements',
    'metrics.measuredAt': 'Measured',
    'profile.heroEyebrow': 'Profile',
    'profile.heroTitle': 'Store the context that makes the dashboard useful.',
    'profile.heroBody': 'Save baseline body data, activity level, and optional custom targets so the app can compare intake against something real.',
    'profile.inputsEyebrow': 'Inputs',
    'profile.inputsHeading': 'Personal settings',
    'profile.inputsSupport': 'Changes save when you tap Save profile. Targets recalculate right after that.',
    'profile.basicsHeading': 'Basic profile',
    'profile.basicsBody': 'Body data used for calorie and macro targets.',
    'profile.lifestyleHeading': 'Lifestyle and goal',
    'profile.lifestyleBody': 'The activity and goal settings shape the recommendation.',
    'profile.adaptiveHeading': 'Adaptive calorie target',
    'profile.adaptiveBody': 'Optionally refine the calculated target from completed activity days. Your profile target remains the fallback.',
    'profile.adaptiveToggle': 'Refine my calorie target from activity',
    'profile.adaptiveToggleHint': 'Uses Oura only when at least 10 recent complete days are available.',
    'profile.adaptiveConnectPrefix': 'Oura is optional.',
    'profile.adaptiveConnectLink': 'Connect or manage it in Health.',
    'profile.adaptiveStatusDisabled': 'Profile target is active',
    'profile.adaptiveStatusNotConnected': 'Oura is not connected',
    'profile.adaptiveStatusWarmingUp': 'Building an activity baseline',
    'profile.adaptiveStatusStale': 'Activity data is out of date',
    'profile.adaptiveStatusCustom': 'Custom calorie target is active',
    'profile.adaptiveStatusActive': 'Adaptive target is active',
    'profile.adaptiveDetailDisabled': 'Turn on adaptive calories if you want activity data to refine this target.',
    'profile.adaptiveDetailNotConnected': 'Your profile target stays active until Oura is connected.',
    'profile.adaptiveDetailWarmingUp': '{days} of 10 complete days available. The profile target remains active for now.',
    'profile.adaptiveDetailStale': 'Sync Oura to resume adaptive targeting. The profile target is being used meanwhile.',
    'profile.adaptiveDetailCustom': 'Your manual calorie value always takes priority over wearable data.',
    'profile.adaptiveDetailActive': 'Based on the median of {days} complete Oura days. Daily changes are limited for stability.',
    'profile.adaptiveBase': 'Profile target',
    'profile.adaptiveBurn': 'Oura burn baseline',
    'profile.adaptiveAdjustment': 'Activity adjustment',
    'profile.adaptiveRange': 'Recommended range',
    'profile.methodProfile': 'Profile estimate (Mifflin-St Jeor)',
    'profile.methodCustom': 'Custom values set by you',
    'profile.methodAdaptive': 'Profile estimate refined by a 14-day Oura baseline',
    'profile.outputsEyebrow': 'Outputs',
    'profile.outputsHeading': 'Current targets',
    'profile.outputsSupport': 'These values update after you save the form.',
    'profile.devicesEyebrow': 'Devices',
    'profile.devicesHeading': 'Connected devices',
    'profile.devicesSupport': 'Sync scale measurements manually when you want to update weight and targets.',
    'profile.withingsNotConfigured': 'Withings is not configured on this server.',
    'profile.withingsDisconnected': 'Withings scale is not connected.',
    'profile.withingsConnected': 'Withings scale is connected.',
    'profile.withingsLatestWeight': 'Latest synced weight: {weight} kg',
    'profile.withingsNoWeight': 'No synced weight yet.',
    'profile.withingsLastSync': 'Last sync: {date}',
    'profile.withingsNeverSynced': 'Not synced yet.',
    'profile.withingsSyncing': 'Syncing Withings measurements...',
    'profile.withingsSynced': 'Withings measurements synced.',
    'profile.withingsConnecting': 'Opening Withings authorization...',
    'profile.withingsConnectedMessage': 'Withings account connected.',
    'profile.withingsConnectionFailed': 'Withings authorization failed.',
    'profile.withingsDisconnectConfirm': 'Disconnect Withings and remove synced measurements?',
    'profile.withingsDisconnectedMessage': 'Withings disconnected.',
    'profile.weightSourceManual': 'Manual profile weight',
    'profile.weightSourceWithings': 'Synced from Withings on {date}',
    'profile.weightSourceEmpty': 'Weight source will appear after you save a weight or sync Withings.',
    'profile.overridesEyebrow': 'Optional overrides',
    'profile.overridesHeading': 'Advanced target overrides',
    'profile.overridesBody': 'Only open this if you want to replace the calculated targets with your own numbers.',
    'profile.targetsEmpty': 'Targets will appear after you save a complete profile.',
    'profile.saving': 'Saving profile...',
    'profile.saved': 'Profile saved.',
    'profile.calories': 'Calories',
    'profile.protein': 'Protein',
    'profile.carbs': 'Carbs',
    'profile.fat': 'Fat',
    'profile.fiber': 'Fiber',
    'profile.method': 'Method',
    'profile.bmr': 'BMR',
    'profile.tdee': 'TDEE',
    'common.unknown': 'Unknown',
  },
  cs: {
    'title.login': 'Food Reader | Přihlášení',
    'title.add': 'Food Reader | Přidat jídlo',
    'title.history': 'Food Reader | Historie',
    'title.metrics': 'Food Reader | Přehled',
    'title.profile': 'Food Reader | Profil',
    'brand.name': 'Food Reader',
    'brand.tagline': 'mobilní nutriční deník',
    'nav.add': 'Přidat jídlo',
    'nav.addShort': 'Přidat',
    'nav.history': 'Historie',
    'nav.metrics': 'Přehled',
    'nav.profile': 'Profil',
    'button.install': 'Instalovat',
    'button.installApp': 'Instalovat aplikaci',
    'button.notNow': 'Teď ne',
    'button.showSteps': 'Ukázat postup',
    'button.logout': 'Odhlásit',
    'button.takePhoto': 'Vyfotit',
    'button.useSavedPhoto': 'Vybrat z galerie',
    'button.choosePhoto': 'Vybrat fotku',
    'button.analyzePhoto': 'Analyzovat jídlo',
    'button.analyzeText': 'Analyzovat text jídla',
    'button.applyRange': 'Použít rozsah',
    'button.refreshMetrics': 'Obnovit přehled',
    'button.saveProfile': 'Uložit profil',
    'button.resetForm': 'Obnovit formulář',
    'button.connectWithings': 'Propojit Withings',
    'button.syncWithings': 'Synchronizovat Withings',
    'button.disconnectWithings': 'Odpojit',
    'button.saveChanges': 'Uložit změny',
    'button.reset': 'Resetovat',
    'button.rerunAnalysis': 'Spustit analýzu znovu',
    'button.openHistory': 'Otevřít historii',
    'button.signIn': 'Přihlásit se',
    'button.createAccount': 'Vytvořit účet',
    'button.close': 'Zavřít',
    'button.review': 'Zkontrolovat',
    'button.logAgain': 'Zapsat znovu',
    'button.remove': 'Odstranit',
    'button.saveFavorite': 'Uložit do oblíbených',
    'button.editMeal': 'Upravit jídlo',
    'button.addAnotherMeal': 'Přidat další jídlo',
    'button.cancelEdit': 'Zrušit úpravy',
    'button.startVoice': 'Spustit diktování',
    'button.stopVoice': 'Zastavit poslech',
    'button.syncQueue': 'Synchronizovat frontu',
    'button.improveEstimate': 'Zpřesnit odhad',
    'button.applyRefinement': 'Aktualizovat odhad',
    'button.openEdit': 'Upravit jídlo',
    'button.editMeal': 'Upravit jídlo',
    'button.saveMeal': 'Uložit jídlo',
    'button.view': 'Zobrazit',
    'button.delete': 'Smazat',
    'button.today': 'Dnes',
    'button.last7': 'Posledních 7 dní',
    'button.last30': 'Posledních 30 dní',
    'button.last90': 'Posledních 90 dní',
    'button.customDates': 'Vlastní datumy',
    'filter.activeRange': 'Aktivní rozsah',
    'label.email': 'E-mail',
    'label.password': 'Heslo',
    'label.name': 'Jméno',
    'label.describeMeal': 'Popis jídla',
    'text.placeholder': 'Například: shawarma bowl s kuřetem, rýží, okurkami, tahini a salátem',
    'label.notes': 'Poznámky',
    'label.mealType': 'Typ jídla',
    'label.consumedAt': 'Snědeno v',
    'label.calories': 'Kalorie',
    'label.protein': 'Bílkoviny (g)',
    'label.fat': 'Tuky (g)',
    'label.carbs': 'Sacharidy (g)',
    'label.fiber': 'Vláknina (g)',
    'label.sugar': 'Cukr (g)',
    'label.sodium': 'Sodík (mg)',
    'label.from': 'Od',
    'label.to': 'Do',
    'label.height': 'Výška (cm)',
    'label.weight': 'Váha (kg)',
    'label.age': 'Věk',
    'label.gender': 'Pohlaví',
    'label.activity': 'Aktivita',
    'label.goal': 'Cíl',
    'label.diet': 'Preferovaná strava',
    'label.customCalories': 'Vlastní kalorie',
    'label.customProtein': 'Vlastní bílkoviny',
    'label.customCarbs': 'Vlastní sacharidy',
    'label.customFat': 'Vlastní tuky',
    'label.customFiber': 'Vlastní vláknina',
    'label.language': 'Jazyk',
    'install.promptFallback': 'Pokud se instalační nabídka neukáže, použijte menu prohlížeče.',
    'install.bannerEyebrow': 'Instalace aplikace',
    'install.bannerTitle': 'Mějte Food Reader hned po ruce',
    'install.bannerBody': 'Nainstalujte aplikaci pro rychlejší spuštění, plnoobrazovkové zapisování a lepší práci offline.',
    'install.fallbackTitle': 'Přidejte Food Reader na plochu',
    'install.fallbackBody': 'Na tomto zařízení použijte menu prohlížeče a přidejte aplikaci na plochu, aby bylo focení jídel hned po ruce.',
    'install.dismissed': 'Instalační výzva byla prozatím skryta.',
    'install.installed': 'Food Reader je nainstalovaný a připravený.',
    'install.iosStep1': 'V Safari klepněte na tlačítko Sdílet.',
    'install.iosStep2': 'Vyberte Přidat na plochu.',
    'install.iosStep3': 'Potvrďte Přidat a Food Reader se uloží do zařízení.',
    'install.instructionsTitle': 'Nainstalujte Food Reader',
    'install.instructionsBody': 'Uložte si aplikaci na plochu pro rychlejší zapisování jídel a čistší celoobrazovkový režim.',
    'install.instructionsHint': 'Stačí to udělat jen jednou.',
    'option.breakfast': 'Snídaně',
    'option.lunch': 'Oběd',
    'option.dinner': 'Večeře',
    'option.snack': 'Svačina',
    'option.choose': 'Vyberte',
    'option.male': 'Muž',
    'option.female': 'Žena',
    'option.other': 'Jiné',
    'option.sedentary': 'Sedavý režim',
    'option.lightly_active': 'Lehce aktivní',
    'option.moderately_active': 'Středně aktivní',
    'option.very_active': 'Velmi aktivní',
    'option.extremely_active': 'Extrémně aktivní',
    'option.weight_loss': 'Hubnutí',
    'option.maintenance': 'Udržování',
    'option.muscle_gain': 'Nabírání svalů',
    'option.none': 'Vyvážená',
    'option.high_protein': 'Vysoký protein',
    'option.low_carb': 'Nízké sacharidy',
    'option.keto': 'Keto',
    'option.vegetarian': 'Vegetariánská',
    'option.vegan': 'Veganská',
    'login.welcomeBack': 'Vítejte zpět',
    'login.signInHeading': 'Přihlášení',
    'login.signInSupport': 'Použijte svůj účet a pokračujte hned dál.',
    'login.newAccount': 'Nový účet',
    'login.createAccess': 'Vytvořit přístup',
    'login.createSupport': 'Vytvořte si účet a ukládejte jídla i historii.',
    'login.newHere': 'Jste tu nově?',
    'login.haveAccount': 'Už účet máte?',
    'login.signingIn': 'Přihlašuji vás...',
    'login.registering': 'Vytvářím účet...',
    'login.registered': 'Účet byl vytvořen. Teď se můžete přihlásit.',
    'home.heroEyebrow': 'Zachyťte rychle, upravte později',
    'home.heroTitle': 'Zapište jídlo během pár vteřin a stále mějte čísla pod kontrolou.',
    'home.heroBody': 'Použijte fotku, text, naskenujte balené jídlo nebo znovu použijte uložené šablony. Každý záznam se stále otevře do kontrolního panelu.',
    'home.todayEyebrow': 'Dnes',
    'home.todayHeading': 'Denní dashboard',
    'home.templatesEyebrow': 'Rychlé použití',
    'home.templatesHeading': 'Oblíbené a šablony',
    'home.captureEyebrow': 'Nový záznam',
    'home.captureHeading': 'Přidat jídlo',
    'home.capturePhoto': 'Fotka',
    'home.captureText': 'Text',
    'home.captureModeHelper': 'Vyberte jeden způsob zápisu stejného jídla. Fotka používá analýzu obrazu, text je plnohodnotná ruční alternativa.',
    'home.mobileCameraHint': 'Otevřete rovnou fotoaparát v telefonu a před uložením výsledek zkontrolujte.',
    'home.uploadHint': 'Vyfoťte nebo nahrajte fotku jídla',
    'home.analysisContextLabel': 'Přidejte detaily pro přesnější analýzu',
    'home.analysisContextHelper': 'Můžete dopsat ingredience, porci, omáčky, nápoje nebo cokoli, co na fotce není dobře vidět.',
    'home.analysisContextPlaceholder': 'Například: dvojitý cheeseburger, snědl jsem jen půlku hranolek, nápoj byl bez cukru',
    'home.analysisLoadingEyebrow': 'Probíhá analýza',
    'home.analysisLoadingTitle': 'Analyzuji vaše jídlo',
    'home.analysisLoadingBody': 'To může trvat několik sekund.',
    'home.analysisLoadingLongWait': 'Stále pracuji. U složitějších jídel to může trvat o pár sekund déle.',
    'home.voiceHint': 'Nadiktujte jídlo a potom odhad zkontrolujte před uložením.',
    'home.recentEyebrow': 'Pokračujte',
    'home.recentHeading': 'Poslední jídla',
    'home.reviewEyebrow': 'Kontrola',
    'home.reviewHeading': 'Upravte návrh nutričních hodnot',
    'home.latestEntry': 'Poslední záznam',
    'home.moreDetailsHeading': 'Další nutriční údaje',
    'home.moreDetailsHint': 'Vláknina, cukr, sodík a kontext jídla',
    'home.correctionHeading': 'Opravte AI rozpoznání',
    'home.correctionPlaceholder': 'Například: bylo to grilované vepřové, ne kuře',
    'home.refineHeading': 'Doplňte chybějící detaily',
    'home.refineHelper': 'Upřesněte porci, skryté ingredience, omáčky, nápoje nebo co jste nesnědli.',
    'home.refinePlaceholder': 'Například: byl to dvojitý burger, snědl jsem jen půlku hranolek a pod houskou byla majonéza',
    'home.insightHighProteinTitle': 'Jídlo s vyšším podílem bílkovin',
    'home.insightHighProteinBody': 'Bílkoviny tvoří výraznou část odhadu, takže by jídlo mělo zasytit lépe než lehká svačina.',
    'home.insightHighFiberTitle': 'Jídlo s dobrou vlákninou',
    'home.insightHighFiberBody': 'Vláknina tu vystupuje nad průměr, takže by energie měla působit stabilněji.',
    'home.insightRichTitle': 'Syté a kaloricky výrazné jídlo',
    'home.insightRichBody': 'Kalorie tu pravděpodobně zvedá kombinace tuků a sacharidů.',
    'home.insightBalancedTitle': 'Vyvážený odhad',
    'home.insightBalancedBody': 'Tohle působí jako středně velké jídlo bez toho, aby jedno makro výrazně převažovalo.',
    'home.templatesEmpty': 'Uložte zkontrolované jídlo nebo produkt a objeví se zde pro jedno klepnutí.',
    'home.queueEmpty': 'Nic nečeká na synchronizaci.',
    'home.queueHeading': 'Offline fronta záznamů',
    'home.queueReady': 'Všechno je synchronizované.',
    'home.queueCompact': 'Na synchronizaci čeká {count} záznamů',
    'home.queueKind.photo': 'Fotka',
    'home.queueKind.text': 'Textový záznam',
    'home.dashboardTargetsMissing': 'Vytvořte profil, aby bylo možné porovnávat dnešek s cílem.',
    'home.dashboardInsights': 'Dnes jste zapsali {meals} jídel a {calories} kcal.',
    'home.dashboardRemaining': 'Zbývá {remaining} kcal',
    'home.dashboardOver': 'Nad cílem o {remaining} kcal',
    'home.dashboardStreak': '{days}denní série zapisování',
    'home.dashboardTemplates': '{count} uložených šablon',
    'home.dashboardQueue': '{count} čekajících záznamů',
    'home.dashboardProtein': 'Dnešní bílkoviny',
    'home.dashboardFiber': 'Dnešní vláknina',
    'home.dashboardCalories': 'Dnešní kalorie',
    'home.dashboardTarget': 'Cíl',
    'home.templateSaved': 'Šablona byla uložena pro rychlé použití.',
    'home.voiceUnsupported': 'Hlasový vstup není v tomto prohlížeči podporován.',
    'home.voiceActive': 'Poslouchám... mluvte přirozeně.',
    'home.voiceStopped': 'Hlasový vstup byl zastaven.',
    'home.queueAddedText': 'Jste offline. Jídlo bylo přidáno do synchronizační fronty.',
    'home.queueAddedPhoto': 'Jste offline. Fotka byla uložena do synchronizační fronty.',
    'home.queueSyncing': 'Synchronizuji čekající jídla...',
    'home.queueSynced': 'Čekající jídla byla synchronizována.',
    'home.queueSyncError': 'Některá čekající jídla stále potřebují připojení.',
    'home.photoRequired': 'Před odesláním vyberte fotku.',
    'home.photoPreparing': 'Připravuji vaši fotku...',
    'home.loadingStageUpload': 'Kontroluji fotku a připravuji obrázek.',
    'home.loadingStageDetect': 'Vyhodnocuji ingredience a velikost porce.',
    'home.loadingStageEstimate': 'Odhaduji kalorie a makra.',
    'home.loadingStageTextRead': 'Vyhodnocuji popis jídla.',
    'home.loadingStageReview': 'Připravuji kontrolní kartu.',
    'home.textRequired': 'Nejdřív popište jídlo.',
    'home.photoAnalyzing': 'Analyzuji fotku jídla...',
    'home.textAnalyzing': 'Analyzuji popis jídla...',
    'home.mealAdded': 'Jídlo bylo přidáno. Zkontrolujte odhad níže.',
    'home.savingAdjustments': 'Ukládám úpravy...',
    'home.mealUpdated': 'Jídlo bylo aktualizováno.',
    'home.mealDeleted': 'Jídlo bylo smazáno.',
    'home.deleteConfirm': 'Smazat toto jídlo natrvalo?',
    'home.resetDone': 'Změny byly vráceny.',
    'home.correctionRequired': 'Před aktualizací odhadu doplňte další detail.',
    'home.refineCancelled': 'Zpřesnění odhadu bylo zrušeno.',
    'home.reanalyzing': 'Provádím novou analýzu...',
    'home.reanalysisUpdated': 'AI analýza byla aktualizována.',
    'home.noMeals': 'Zatím tu nejsou žádná jídla. Přidejte první.',
    'history.heroEyebrow': 'Historie',
    'history.heroTitle': 'Projděte celý deník v rozložení, které funguje i na telefonu.',
    'history.heroBody': 'Filtrujte datumy, rychle najděte odlehlé záznamy a upravujte je bez opuštění historie.',
    'history.filterEyebrow': 'Rozsah',
    'history.filterHeading': 'Filtrovat historii',
    'history.templatesEyebrow': 'Znovu použít',
    'history.templatesHeading': 'Uložené šablony',
    'history.summary.totalMeals': 'Počet jídel',
    'history.summary.totalCalories': 'Celkem kalorií',
    'history.summary.avgPerMeal': 'Průměr na jídlo',
    'history.mealsLabel': 'jídel',
    'history.empty': 'Tomuto rozsahu neodpovídají žádná jídla.',
    'history.noNotes': 'Zatím bez poznámek.',
    'history.loading': 'Načítám historii jídel...',
    'history.deleted': 'Jídlo bylo smazáno.',
    'history.deleting': 'Mažu jídlo...',
    'history.saving': 'Ukládám změny...',
    'history.saved': 'Jídlo bylo aktualizováno.',
    'history.deleteConfirm': 'Smazat toto jídlo natrvalo?',
    'metrics.heroEyebrow': 'Přehled',
    'metrics.heroTitle': 'Podívejte se, jestli se denní vzorec blíží cíli.',
    'metrics.heroBody': 'Dashboard je čitelný i na úzkém mobilu, ale na větších obrazovkách nabídne hustší přehled.',
    'metrics.loading': 'Načítám přehled...',
    'metrics.todayEyebrow': 'Dnes',
    'metrics.todayHeading': 'Stav denního cíle',
    'metrics.todayOnTrack': 'Dnes jste v plánu',
    'metrics.todayOverGoal': 'Dnes jste nad cílem',
    'metrics.todayNoMeals': 'Dnes zatím nemáte zapsané žádné jídlo.',
    'metrics.todayNoTarget': 'Nastavte si profilový cíl, aby šlo dnešek správně vyhodnotit.',
    'metrics.todayConsumed': '{calories} z {target} kcal',
    'metrics.todayNoTargetConsumed': 'Dnes zapsáno {calories} kcal',
    'metrics.todayRemaining': 'Dnes zbývá {remaining} kcal',
    'metrics.todayOverAmount': 'Nad cílem o {remaining} kcal',
    'metrics.todayMeals': 'Dnešní jídla',
    'metrics.todayProtein': 'Dnešní bílkoviny',
    'metrics.todayCarbs': 'Dnešní sacharidy',
    'metrics.todayFat': 'Dnešní tuky',
    'metrics.todayFiber': 'Dnešní vláknina',
    'metrics.adaptiveTarget': 'Adaptivní cíl podle aktivity',
    'metrics.adaptiveTargetDetail': 'Dnešní cíl je zpřesněný podle dokončených dnů aktivity z Oury.',
    'metrics.filterNote': 'Tento filtr ovládá vše níže. Horní karta vždy ukazuje jen dnešek.',
    'metrics.filterEyebrow': 'Rozsah',
    'metrics.filterHeading': 'Filtrovat analýzu',
    'metrics.avgPerDay': 'průměr/den',
    'metrics.rangeEyebrow': 'Vybraný rozsah',
    'metrics.rangeHeading': 'Souhrn rozsahu',
    'metrics.targetsEyebrow': 'Nastavení cíle',
    'metrics.targetsHeading': 'Aktuální cíle',
    'metrics.avgDailyCalories': 'Průměrné denní kalorie',
    'metrics.totalCalories': 'Celkem kalorií',
    'metrics.totalMeals': 'Celkem jídel',
    'metrics.fiberLogged': 'Zapsaná vláknina',
    'metrics.calories': 'Kalorie',
    'metrics.protein': 'Bílkoviny',
    'metrics.carbs': 'Sacharidy',
    'metrics.fat': 'Tuky',
    'metrics.fiber': 'Vláknina',
    'metrics.mealsLabel': 'jídel',
    'metrics.macroKcal': 'makro kcal',
    'metrics.noMacroData': 'Rozložení maker se objeví po zapsání jídel.',
    'metrics.progressEyebrow': 'Pokrok',
    'metrics.progressHeading': 'Průměrný příjem vůči cíli',
    'metrics.dailyEyebrow': 'Denní kalorie',
    'metrics.dailyHeading': 'Sloupcový přehled',
    'metrics.macroEyebrow': 'Makra',
    'metrics.macroHeading': 'Rozložení',
    'metrics.dayByDayEyebrow': 'Den po dni',
    'metrics.dayByDayHeading': 'Souhrnný seznam',
    'metrics.targetsMissing': 'Vytvořte profil a odemkněte osobní cíle pro kalorie a makra.',
    'metrics.setupProfile': 'Nastavit profil',
    'metrics.dayListEmpty': 'Denní rozpad se objeví po zapsání jídel.',
    'metrics.bodyEyebrow': 'Tělesné metriky',
    'metrics.bodyHeading': 'Trend váhy z Withings',
    'metrics.bodyEmpty': 'Propojte Withings a synchronizujte váhu, aby se tu zobrazily tělesné metriky.',
    'metrics.latestWeight': 'Poslední váha',
    'metrics.weightChange': 'Změna váhy',
    'metrics.bodyFat': 'Tělesný tuk',
    'metrics.muscleMass': 'Svalová hmota',
    'metrics.measurements': 'měření',
    'metrics.measuredAt': 'Změřeno',
    'profile.heroEyebrow': 'Profil',
    'profile.heroTitle': 'Uložte kontext, který dělá dashboard užitečným.',
    'profile.heroBody': 'Uložte základní tělesná data, aktivitu a případné vlastní cíle, aby aplikace porovnávala příjem s realitou.',
    'profile.inputsEyebrow': 'Vstupy',
    'profile.inputsHeading': 'Osobní nastavení',
    'profile.inputsSupport': 'Změny se uloží po klepnutí na Uložit profil. Cíle se hned přepočítají.',
    'profile.basicsHeading': 'Základní profil',
    'profile.basicsBody': 'Tělesné údaje, ze kterých se počítají cíle.',
    'profile.lifestyleHeading': 'Životní styl a cíl',
    'profile.lifestyleBody': 'Aktivita a cíl určují doporučení.',
    'profile.adaptiveHeading': 'Adaptivní kalorický cíl',
    'profile.adaptiveBody': 'Vypočítaný cíl lze volitelně zpřesnit podle dokončených dnů aktivity. Profilový cíl vždy zůstává zálohou.',
    'profile.adaptiveToggle': 'Zpřesňovat kalorický cíl podle aktivity',
    'profile.adaptiveToggleHint': 'Oura se použije až při nejméně 10 nedávných úplných dnech.',
    'profile.adaptiveConnectPrefix': 'Oura je volitelná.',
    'profile.adaptiveConnectLink': 'Propojte nebo spravujte ji v záložce Zdraví.',
    'profile.adaptiveStatusDisabled': 'Aktivní je profilový cíl',
    'profile.adaptiveStatusNotConnected': 'Oura není připojená',
    'profile.adaptiveStatusWarmingUp': 'Vytváří se základ aktivity',
    'profile.adaptiveStatusStale': 'Data o aktivitě nejsou aktuální',
    'profile.adaptiveStatusCustom': 'Aktivní je vlastní kalorický cíl',
    'profile.adaptiveStatusActive': 'Adaptivní cíl je aktivní',
    'profile.adaptiveDetailDisabled': 'Pokud chcete cíl zpřesňovat aktivitou, zapněte adaptivní kalorie.',
    'profile.adaptiveDetailNotConnected': 'Dokud nepropojíte Ouru, zůstane aktivní profilový cíl.',
    'profile.adaptiveDetailWarmingUp': 'K dispozici je {days} z 10 úplných dnů. Zatím zůstává aktivní profilový cíl.',
    'profile.adaptiveDetailStale': 'Synchronizujte Ouru. Do té doby aplikace používá profilový cíl.',
    'profile.adaptiveDetailCustom': 'Ručně nastavená hodnota kalorií má vždy přednost před daty ze zařízení.',
    'profile.adaptiveDetailActive': 'Vychází z mediánu {days} úplných dnů Oury. Denní změny jsou kvůli stabilitě omezené.',
    'profile.adaptiveBase': 'Profilový cíl',
    'profile.adaptiveBurn': 'Základ výdeje z Oury',
    'profile.adaptiveAdjustment': 'Úprava podle aktivity',
    'profile.adaptiveRange': 'Doporučené rozmezí',
    'profile.methodProfile': 'Odhad z profilu (Mifflin-St Jeor)',
    'profile.methodCustom': 'Vlastní hodnoty nastavené uživatelem',
    'profile.methodAdaptive': 'Profilový odhad zpřesněný 14denním základem Oury',
    'profile.outputsEyebrow': 'Výstupy',
    'profile.outputsHeading': 'Aktuální cíle',
    'profile.outputsSupport': 'Tyto hodnoty se aktualizují po uložení formuláře.',
    'profile.devicesEyebrow': 'Zařízení',
    'profile.devicesHeading': 'Připojená zařízení',
    'profile.devicesSupport': 'Měření z váhy synchronizujte ručně, když chcete aktualizovat váhu a cíle.',
    'profile.withingsNotConfigured': 'Withings není na tomto serveru nakonfigurovaný.',
    'profile.withingsDisconnected': 'Withings váha není připojená.',
    'profile.withingsConnected': 'Withings váha je připojená.',
    'profile.withingsLatestWeight': 'Poslední synchronizovaná váha: {weight} kg',
    'profile.withingsNoWeight': 'Zatím není synchronizovaná žádná váha.',
    'profile.withingsLastSync': 'Poslední sync: {date}',
    'profile.withingsNeverSynced': 'Zatím nesynchronizováno.',
    'profile.withingsSyncing': 'Synchronizuji měření z Withings...',
    'profile.withingsSynced': 'Měření z Withings byla synchronizována.',
    'profile.withingsConnecting': 'Otevírám autorizaci Withings...',
    'profile.withingsConnectedMessage': 'Withings účet byl propojen.',
    'profile.withingsConnectionFailed': 'Autorizace Withings selhala.',
    'profile.withingsDisconnectConfirm': 'Odpojit Withings a odstranit synchronizovaná měření?',
    'profile.withingsDisconnectedMessage': 'Withings byl odpojen.',
    'profile.weightSourceManual': 'Ručně zadaná váha v profilu',
    'profile.weightSourceWithings': 'Synchronizováno z Withings dne {date}',
    'profile.weightSourceEmpty': 'Zdroj váhy se zobrazí po uložení váhy nebo synchronizaci Withings.',
    'profile.overridesEyebrow': 'Volitelné přepisy',
    'profile.overridesHeading': 'Pokročilé přepisy cílů',
    'profile.overridesBody': 'Otevírejte jen tehdy, když chcete nahradit vypočítané cíle vlastními čísly.',
    'profile.targetsEmpty': 'Cíle se zobrazí po uložení kompletního profilu.',
    'profile.saving': 'Ukládám profil...',
    'profile.saved': 'Profil byl uložen.',
    'profile.calories': 'Kalorie',
    'profile.protein': 'Bílkoviny',
    'profile.carbs': 'Sacharidy',
    'profile.fat': 'Tuky',
    'profile.fiber': 'Vláknina',
    'profile.method': 'Metoda',
    'profile.bmr': 'BMR',
    'profile.tdee': 'TDEE',
    'common.unknown': 'Neznámé',
  },
};

function safeWindowAvailable() {
  return typeof window !== 'undefined';
}

function createLocalId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function interpolate(template, variables = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) => String(variables[key] ?? ''));
}

function getStorageKey(namespace) {
  const scope = currentUserContext?.id ? `user:${currentUserContext.id}` : 'guest';
  return `${APP_STORAGE_PREFIX}:${scope}:${namespace}`;
}

function readStoredJson(key, fallback) {
  if (!safeWindowAvailable()) {
    return fallback;
  }

  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeStoredJson(key, value) {
  if (!safeWindowAvailable()) {
    return;
  }

  window.localStorage.setItem(key, JSON.stringify(value));
}

function dispatchAppEvent(name, detail) {
  if (!safeWindowAvailable()) {
    return;
  }

  window.dispatchEvent(new CustomEvent(name, { detail }));
}

export function getLocale() {
  return SUPPORTED_LOCALES.includes(currentLocale) ? currentLocale : 'en';
}

export function t(key, variables = {}) {
  const locale = getLocale();
  const value =
    TRANSLATIONS[locale]?.[key] ??
    TRANSLATIONS.en?.[key] ??
    key;

  return interpolate(value, variables);
}

export function setLocale(locale) {
  const normalized = SUPPORTED_LOCALES.includes(locale) ? locale : 'en';
  currentLocale = normalized;
  if (safeWindowAvailable()) {
    window.localStorage.setItem(`${APP_STORAGE_PREFIX}:locale`, normalized);
  }
  applyTranslations();
  dispatchAppEvent('food-reader:localechange', { locale: normalized });
}

export function applyTranslations(root = document) {
  if (typeof document === 'undefined') {
    return;
  }

  document.documentElement.lang = getLocale();

  root.querySelectorAll('[data-i18n]').forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  root.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
    element.setAttribute('placeholder', t(element.dataset.i18nPlaceholder));
  });
  root.querySelectorAll('[data-i18n-title]').forEach((element) => {
    element.setAttribute('title', t(element.dataset.i18nTitle));
  });
  root.querySelectorAll('[data-i18n-aria-label]').forEach((element) => {
    element.setAttribute('aria-label', t(element.dataset.i18nAriaLabel));
  });

  const page = document.body?.dataset.page;
  if (page) {
    document.title = t(`title.${page}`);
  }
}

export function setupLanguageControls() {
  if (typeof document === 'undefined') {
    return;
  }

  document.querySelectorAll('[data-language-select]').forEach((control) => {
    control.value = getLocale();
    control.addEventListener('change', (event) => {
      setLocale(event.currentTarget.value);
    });
  });
}

export function setCurrentUserContext(user) {
  currentUserContext = user;
}

export function getCurrentUserContext() {
  return currentUserContext;
}

export function getMealTemplates() {
  return readStoredJson(getStorageKey('meal-templates'), []);
}

export function saveMealTemplate(template) {
  const templates = getMealTemplates();
  const nextTemplate = {
    favorite: true,
    created_at: new Date().toISOString(),
    id: template.id || createLocalId(),
    ...template,
  };
  const nextTemplates = [nextTemplate, ...templates.filter((item) => item.id !== nextTemplate.id)];
  writeStoredJson(getStorageKey('meal-templates'), nextTemplates.slice(0, 30));
  dispatchAppEvent('food-reader:templateschange', { templates: nextTemplates });
  return nextTemplate;
}

export function deleteMealTemplate(templateId) {
  const templates = getMealTemplates().filter((item) => item.id !== templateId);
  writeStoredJson(getStorageKey('meal-templates'), templates);
  dispatchAppEvent('food-reader:templateschange', { templates });
  return templates;
}

export function getPendingMealQueue() {
  return readStoredJson(getStorageKey('pending-meals'), []);
}

export function queuePendingMeal(entry) {
  const queue = getPendingMealQueue();
  const nextEntry = {
    id: createLocalId(),
    queued_at: new Date().toISOString(),
    ...entry,
  };
  const nextQueue = [nextEntry, ...queue];
  writeStoredJson(getStorageKey('pending-meals'), nextQueue);
  dispatchAppEvent('food-reader:queuechange', { queue: nextQueue });
  return nextEntry;
}

export function removePendingMeal(entryId) {
  const queue = getPendingMealQueue().filter((item) => item.id !== entryId);
  writeStoredJson(getStorageKey('pending-meals'), queue);
  dispatchAppEvent('food-reader:queuechange', { queue });
  return queue;
}

export function shouldUseSplitLocalApi(locationLike) {
  const port = String(locationLike?.port || '');
  const likelyStaticDevPorts = new Set(['8080', '4173', '5173', '5500']);
  return likelyStaticDevPorts.has(port);
}

function resolveApiBaseUrl() {
  if (typeof window === 'undefined') {
    return '';
  }

  const { protocol, hostname, port } = window.location;
  const locationLike = { protocol, hostname, port };
  const storedBaseUrl = window.localStorage.getItem('food-reader-api-base');
  const runtimeBaseUrl =
    window.FOOD_READER_API_BASE ||
    document.querySelector('meta[name="food-reader-api-base"]')?.content;
  const splitLocalBaseUrl = `${protocol}//${hostname}:8000`;

  if (storedBaseUrl) {
    const normalizedStoredBaseUrl = normalizeBaseUrl(storedBaseUrl);

    // Ignore the old split-dev override when the app is served by Nginx on 18080.
    if (shouldUseSplitLocalApi(locationLike) || normalizedStoredBaseUrl !== splitLocalBaseUrl) {
      return normalizedStoredBaseUrl;
    }
  }

  if (runtimeBaseUrl) {
    return normalizeBaseUrl(runtimeBaseUrl);
  }

  if (shouldUseSplitLocalApi(locationLike)) {
    return splitLocalBaseUrl;
  }

  return '';
}

export const API_BASE_URL = resolveApiBaseUrl();

export const API = {
  login: `${API_BASE_URL}/auth/login`,
  register: `${API_BASE_URL}/auth/register`,
  currentUser: `${API_BASE_URL}/users/me`,
  meals: `${API_BASE_URL}/me/meals`,
  summary: `${API_BASE_URL}/me/summary`,
  profile: `${API_BASE_URL}/profile`,
  withings: `${API_BASE_URL}/withings`,
  oura: `${API_BASE_URL}/oura`,
};

export function resolveAssetUrl(url) {
  if (!url) {
    return url;
  }

  if (/^https?:\/\//i.test(url) || url.startsWith('data:') || url.startsWith('blob:')) {
    return url;
  }

  if (url.startsWith('/uploads/')) {
    return `${API_BASE_URL}${url}`;
  }

  return url;
}

function capitalizeLabel(value) {
  if (!value) {
    return '';
  }

  return value.charAt(0).toUpperCase() + value.slice(1);
}

function truncateLabel(value, maxLength = 40) {
  if (value.length <= maxLength) {
    return value;
  }

  const truncated = value.slice(0, maxLength).trim();
  const lastSpace = truncated.lastIndexOf(' ');
  return `${(lastSpace > 12 ? truncated.slice(0, lastSpace) : truncated).trim()}...`;
}

export function getMealDisplayName(meal) {
  const fallbackKey = meal?.meal_type ? `option.${meal.meal_type}` : 'common.unknown';
  const fallback = capitalizeLabel(t(fallbackKey));
  const notes = String(meal?.notes || '').trim();

  if (!notes) {
    return fallback;
  }

  const prefixes = [
    /^ai analysis:\s*/i,
    /^updated ai analysis:\s*/i,
    /^ai notes:\s*/i,
    /^reanalysis with corrections:\s*/i,
    /^user context:\s*/i,
    /^original user context:\s*/i,
    /^refinement context:\s*/i,
    /^text description:\s*/i,
    /^estimated from:\s*/i,
  ];
  const genericNames = new Set([
    'unknown food',
    'could not analyze the image properly',
    'could not analyze the food description properly',
    'openai api key is not configured',
  ]);

  const segments = notes
    .split(/\n+/)
    .map((segment) => segment.trim())
    .filter(Boolean);

  for (const segment of segments) {
    const cleanedSegment = prefixes.reduce(
      (value, pattern) => value.replace(pattern, ''),
      segment,
    );
    const candidate = cleanedSegment
      .split(/[.!?](?:\s|$)/)[0]
      .replace(/\s+/g, ' ')
      .replace(/^[:\-–\s]+|[:\-–\s]+$/g, '')
      .trim();

    if (!candidate || genericNames.has(candidate.toLowerCase())) {
      continue;
    }

    return truncateLabel(capitalizeLabel(candidate));
  }

  return fallback;
}

export const FRONTEND_ASSET_VERSION = '20260809-5';

const INSTALL_PROMPT_DELAY_MS = 1800;
const INSTALL_RESHOW_AFTER_SHOW_MS = 18 * 60 * 60 * 1000;
const INSTALL_RESHOW_AFTER_DISMISS_MS = 3 * 24 * 60 * 60 * 1000;
const INSTALL_PROMPT_STATE_KEY = `${APP_STORAGE_PREFIX}:install-prompt-state`;
const INSTALL_PROMPT_ANALYTICS_KEY = `${APP_STORAGE_PREFIX}:install-prompt-analytics`;

let deferredInstallPrompt = null;
let installPromptElements = null;
let installPromptTimeoutId = null;

function readGlobalJson(key, fallback) {
  if (!safeWindowAvailable()) {
    return fallback;
  }

  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeGlobalJson(key, value) {
  if (!safeWindowAvailable()) {
    return;
  }

  window.localStorage.setItem(key, JSON.stringify(value));
}

function getInstallPromptState() {
  return readGlobalJson(INSTALL_PROMPT_STATE_KEY, {
    dismissedAt: null,
    installedAt: null,
    lastShownAt: null,
  });
}

function updateInstallPromptState(patch) {
  const nextState = {
    ...getInstallPromptState(),
    ...patch,
  };
  writeGlobalJson(INSTALL_PROMPT_STATE_KEY, nextState);
  return nextState;
}

function isStandaloneDisplayMode() {
  if (!safeWindowAvailable()) {
    return false;
  }

  if (window.matchMedia?.('(display-mode: standalone)').matches) {
    return true;
  }

  return window.navigator?.standalone === true;
}

function isIosLike(navigatorLike = safeWindowAvailable() ? window.navigator : undefined) {
  const userAgent = navigatorLike?.userAgent || '';
  const platform = navigatorLike?.platform || '';
  const maxTouchPoints = Number(navigatorLike?.maxTouchPoints || 0);
  return /iphone|ipad|ipod/i.test(userAgent) || (platform === 'MacIntel' && maxTouchPoints > 1);
}

function isIosInstallFallbackEligible(navigatorLike = safeWindowAvailable() ? window.navigator : undefined) {
  const userAgent = navigatorLike?.userAgent || '';
  const isSafari = /safari/i.test(userAgent) && !/crios|fxios|edgios|optios/i.test(userAgent);
  return isIosLike(navigatorLike) && isSafari && !isStandaloneDisplayMode();
}

function canPromptForInstall() {
  return Boolean(deferredInstallPrompt) && !isStandaloneDisplayMode();
}

export function shouldAutoShowInstallPrompt(state = getInstallPromptState(), now = Date.now()) {
  if (state?.installedAt) {
    return false;
  }

  const dismissedAt = state?.dismissedAt ? new Date(state.dismissedAt).getTime() : 0;
  if (dismissedAt && now - dismissedAt < INSTALL_RESHOW_AFTER_DISMISS_MS) {
    return false;
  }

  const lastShownAt = state?.lastShownAt ? new Date(state.lastShownAt).getTime() : 0;
  if (lastShownAt && now - lastShownAt < INSTALL_RESHOW_AFTER_SHOW_MS) {
    return false;
  }

  return true;
}

function trackInstallEvent(type, detail = {}) {
  const payload = {
    id: createLocalId(),
    type,
    timestamp: new Date().toISOString(),
    locale: getLocale(),
    page: document.body?.dataset.page || null,
    ...detail,
  };

  const events = readGlobalJson(INSTALL_PROMPT_ANALYTICS_KEY, []);
  writeGlobalJson(INSTALL_PROMPT_ANALYTICS_KEY, [...events.slice(-39), payload]);
  dispatchAppEvent(`food-reader:${type}`, payload);
  return payload;
}

export function getAuthToken() {
  return window.localStorage.getItem('token');
}

export function setAuthToken(token) {
  window.localStorage.setItem('token', token);
}

export function clearAuthToken() {
  window.localStorage.removeItem('token');
}

export function isAuthenticated() {
  return Boolean(getAuthToken());
}

export function logout() {
  clearAuthToken();
  if (typeof window !== 'undefined') {
    window.location.href = 'login.html';
  }
}

export function authHeaders(headers = {}) {
  const token = getAuthToken();
  return token ? { ...headers, Authorization: `Bearer ${token}` } : headers;
}

export async function apiFetch(url, options = {}) {
  const {
    auth = true,
    redirectOnAuthError = true,
    headers = {},
    body,
    ...rest
  } = options;

  const resolvedHeaders = new Headers(auth ? authHeaders(headers) : headers);
  const requestOptions = { ...rest, headers: resolvedHeaders };

  if (body !== undefined) {
    if (body instanceof FormData) {
      requestOptions.body = body;
    } else if (typeof body === 'string') {
      requestOptions.body = body;
    } else {
      if (!resolvedHeaders.has('Content-Type')) {
        resolvedHeaders.set('Content-Type', 'application/json');
      }
      requestOptions.body = JSON.stringify(body);
    }
  }

  const response = await fetch(url, requestOptions);
  if (response.status === 401 && redirectOnAuthError) {
    clearAuthToken();
    if (!window.location.pathname.endsWith('login.html')) {
      window.location.href = 'login.html';
    }
  }

  return response;
}

export async function getJsonOrThrow(response, fallbackMessage = 'Request failed') {
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || fallbackMessage);
  }
  return data;
}

export async function fetchCurrentUser() {
  const response = await apiFetch(API.currentUser);
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export function showStatus(target, message = '', tone = 'info') {
  if (!target) {
    return;
  }

  target.textContent = message;
  target.dataset.tone = tone;
  target.hidden = !message;
}

export function formatDateTime(value) {
  if (!value) {
    return t('common.unknown');
  }

  return new Intl.DateTimeFormat(getLocale(), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}

export function formatTime(value) {
  if (!value) {
    return t('common.unknown');
  }

  return new Intl.DateTimeFormat(getLocale(), {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}

export function formatDayLabel(value) {
  return new Intl.DateTimeFormat(getLocale(), {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  }).format(new Date(value));
}

export function parseDateInputValue(value) {
  if (!value) {
    return null;
  }

  const [year, month, day] = value.split('-').map(Number);
  if (!year || !month || !day) {
    return null;
  }

  return new Date(year, month - 1, day);
}

export function getLocalDateKey(value) {
  const date = new Date(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function getDefaultDateRange(daysBack = 6) {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - daysBack);

  return {
    from: toDateInputValue(start),
    to: toDateInputValue(end),
  };
}

export function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function toDateTimeInputValue(value) {
  const date = new Date(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function localDateRangeToUtc(fromDate, toDate) {
  const from = parseDateInputValue(fromDate);
  const to = parseDateInputValue(toDate);

  if (to) {
    to.setDate(to.getDate() + 1);
  }

  return {
    from: from ? from.toISOString() : null,
    to: to ? to.toISOString() : null,
  };
}

export function getBrowserTimeZone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}

export function normalizeOptionalNumber(value) {
  if (value === '' || value === null || value === undefined) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function bindQuickRangeButtons(buttons, onSelect) {
  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      const days = Number(button.dataset.days || 0);
      const range = getDefaultDateRange(days);
      onSelect(range);
    });
  });
}

export function setActiveNavLink() {
  const page = document.body.dataset.page;
  document.querySelectorAll('[data-nav]').forEach((link) => {
    link.classList.toggle('active', link.dataset.nav === page);
  });
}

export function toggleModal(modal, shouldOpen) {
  if (!modal) {
    return;
  }
  modal.hidden = !shouldOpen;
  document.body.classList.toggle('modal-open', shouldOpen);
}

function getInstallPromptMode() {
  if (canPromptForInstall()) {
    return 'prompt';
  }

  if (isIosInstallFallbackEligible()) {
    return 'ios-fallback';
  }

  return 'unavailable';
}

function closeInstallInstructions() {
  if (!installPromptElements?.modal) {
    return;
  }

  toggleModal(installPromptElements.modal, false);
}

function hideInstallPromptBanner() {
  if (!installPromptElements?.banner) {
    return;
  }

  installPromptElements.banner.classList.remove('visible');
  window.setTimeout(() => {
    if (installPromptElements?.banner && !installPromptElements.banner.classList.contains('visible')) {
      installPromptElements.banner.hidden = true;
    }
  }, 220);
}

function updateInstallPromptUi() {
  if (!safeWindowAvailable()) {
    return 'unavailable';
  }

  const mode = getInstallPromptMode();
  const installed = isStandaloneDisplayMode() || Boolean(getInstallPromptState().installedAt);
  const installButtons = document.querySelectorAll('[data-install-button]');
  const canShowEntryPoint = !installed && mode !== 'unavailable';

  installButtons.forEach((button) => {
    button.hidden = !canShowEntryPoint;
    button.textContent = t('button.install');
  });

  if (!installPromptElements) {
    return mode;
  }

  installPromptElements.banner.dataset.mode = mode;
  installPromptElements.title.textContent =
    mode === 'ios-fallback' ? t('install.fallbackTitle') : t('install.bannerTitle');
  installPromptElements.body.textContent =
    mode === 'ios-fallback' ? t('install.fallbackBody') : t('install.bannerBody');
  installPromptElements.cta.textContent =
    mode === 'ios-fallback' ? t('button.showSteps') : t('button.installApp');
  installPromptElements.dismiss.textContent = t('button.notNow');
  installPromptElements.eyebrow.textContent = t('install.bannerEyebrow');
  installPromptElements.modalEyebrow.textContent = t('install.bannerEyebrow');
  installPromptElements.modalTitle.textContent = t('install.instructionsTitle');
  installPromptElements.modalBody.textContent = t('install.instructionsBody');
  installPromptElements.modalHint.textContent = t('install.instructionsHint');
  installPromptElements.stepOne.textContent = t('install.iosStep1');
  installPromptElements.stepTwo.textContent = t('install.iosStep2');
  installPromptElements.stepThree.textContent = t('install.iosStep3');
  installPromptElements.modalClose.textContent = t('button.close');

  if (!canShowEntryPoint) {
    hideInstallPromptBanner();
    closeInstallInstructions();
  }

  return mode;
}

function createInstallPromptUi() {
  if (installPromptElements || typeof document === 'undefined') {
    return installPromptElements;
  }

  const banner = document.createElement('section');
  banner.id = 'installPromptBanner';
  banner.className = 'install-prompt-banner';
  banner.hidden = true;
  banner.setAttribute('aria-live', 'polite');
  banner.innerHTML = `
    <div class="install-prompt-card">
      <button type="button" class="install-prompt-dismiss" data-install-dismiss aria-label="Dismiss install prompt">×</button>
      <div class="install-prompt-mark" aria-hidden="true">FR</div>
      <div class="install-prompt-copy">
        <p class="eyebrow" data-install-eyebrow></p>
        <h2 data-install-title></h2>
        <p data-install-body></p>
      </div>
      <div class="install-prompt-actions">
        <button type="button" class="btn btn-primary btn-block" data-install-cta></button>
        <button type="button" class="btn btn-secondary btn-block" data-install-later></button>
      </div>
    </div>
  `;

  const modal = document.createElement('section');
  modal.id = 'installHelpModal';
  modal.className = 'modal';
  modal.hidden = true;
  modal.innerHTML = `
    <div class="modal-card install-help-card">
      <button type="button" class="modal-close" data-install-help-close aria-label="Close install help">×</button>
      <div class="stack">
        <div>
          <p class="eyebrow" data-install-help-eyebrow></p>
          <h2 data-install-help-title></h2>
          <p class="panel-note" data-install-help-body></p>
        </div>
        <div class="install-help-steps">
          <div class="install-help-step">
            <span>1</span>
            <p data-install-help-step-one></p>
          </div>
          <div class="install-help-step">
            <span>2</span>
            <p data-install-help-step-two></p>
          </div>
          <div class="install-help-step">
            <span>3</span>
            <p data-install-help-step-three></p>
          </div>
        </div>
        <p class="install-help-hint" data-install-help-hint></p>
        <button type="button" class="btn btn-primary btn-block" data-install-help-done></button>
      </div>
    </div>
  `;

  document.body.appendChild(banner);
  document.body.appendChild(modal);

  installPromptElements = {
    banner,
    modal,
    eyebrow: banner.querySelector('[data-install-eyebrow]'),
    title: banner.querySelector('[data-install-title]'),
    body: banner.querySelector('[data-install-body]'),
    cta: banner.querySelector('[data-install-cta]'),
    dismiss: banner.querySelector('[data-install-later]'),
    dismissIcon: banner.querySelector('[data-install-dismiss]'),
    modalTitle: modal.querySelector('[data-install-help-title]'),
    modalBody: modal.querySelector('[data-install-help-body]'),
    modalHint: modal.querySelector('[data-install-help-hint]'),
    modalEyebrow: modal.querySelector('[data-install-help-eyebrow]'),
    stepOne: modal.querySelector('[data-install-help-step-one]'),
    stepTwo: modal.querySelector('[data-install-help-step-two]'),
    stepThree: modal.querySelector('[data-install-help-step-three]'),
    modalClose: modal.querySelector('[data-install-help-done]'),
  };

  installPromptElements.dismiss.addEventListener('click', () => {
    updateInstallPromptState({ dismissedAt: new Date().toISOString() });
    trackInstallEvent('installdismissed', { source: 'banner' });
    hideInstallPromptBanner();
  });

  installPromptElements.dismissIcon.addEventListener('click', () => {
    updateInstallPromptState({ dismissedAt: new Date().toISOString() });
    trackInstallEvent('installdismissed', { source: 'icon' });
    hideInstallPromptBanner();
  });

  installPromptElements.cta.addEventListener('click', () => {
    void handleInstallCallToAction('banner');
  });

  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      closeInstallInstructions();
    }
  });

  modal.querySelector('[data-install-help-close]').addEventListener('click', closeInstallInstructions);
  installPromptElements.modalClose.addEventListener('click', closeInstallInstructions);

  updateInstallPromptUi();
  return installPromptElements;
}

function openInstallInstructions(source = 'manual') {
  createInstallPromptUi();
  updateInstallPromptUi();
  toggleModal(installPromptElements.modal, true);
  trackInstallEvent('installpromptshown', { source, mode: 'ios-fallback-instructions' });
}

function showInstallPromptBanner({ force = false, source = 'auto' } = {}) {
  createInstallPromptUi();
  const mode = updateInstallPromptUi();

  if (mode === 'unavailable') {
    return false;
  }

  if (!force && !shouldAutoShowInstallPrompt()) {
    return false;
  }

  updateInstallPromptState({ lastShownAt: new Date().toISOString() });
  installPromptElements.banner.hidden = false;
  const scheduleFrame = window.requestAnimationFrame || ((callback) => window.setTimeout(callback, 0));
  scheduleFrame(() => {
    installPromptElements?.banner.classList.add('visible');
  });
  trackInstallEvent('installpromptshown', { source, mode });
  return true;
}

function scheduleInstallPrompt() {
  window.clearTimeout(installPromptTimeoutId);

  const state = getInstallPromptState();
  if (!shouldAutoShowInstallPrompt(state)) {
    return;
  }

  const mode = updateInstallPromptUi();
  if (mode === 'unavailable') {
    return;
  }

  installPromptTimeoutId = window.setTimeout(() => {
    showInstallPromptBanner({ source: 'auto' });
  }, INSTALL_PROMPT_DELAY_MS);
}

async function handleInstallCallToAction(source = 'manual') {
  const mode = updateInstallPromptUi();

  if (mode === 'ios-fallback') {
    trackInstallEvent('installctaclicked', { source, mode });
    hideInstallPromptBanner();
    openInstallInstructions(source);
    return;
  }

  if (!deferredInstallPrompt) {
    showToast(t('install.promptFallback'));
    return;
  }

  trackInstallEvent('installctaclicked', { source, mode: 'prompt' });
  hideInstallPromptBanner();

  const promptEvent = deferredInstallPrompt;
  deferredInstallPrompt = null;

  try {
    await promptEvent.prompt();
    const choice = await promptEvent.userChoice;
    if (choice?.outcome !== 'accepted') {
      updateInstallPromptState({ dismissedAt: new Date().toISOString() });
      trackInstallEvent('installdismissed', { source: `${source}-browser`, mode: 'prompt' });
    }
  } catch (error) {
    console.error('Install prompt failed:', error);
  }

  updateInstallPromptUi();
}

export async function registerServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }

  try {
    await navigator.serviceWorker.register(`/service-worker.js?v=${FRONTEND_ASSET_VERSION}`);
  } catch (error) {
    console.error('Service worker registration failed:', error);
  }
}

export function setupInstallPrompt() {
  if (typeof document === 'undefined') {
    return;
  }

  createInstallPromptUi();

  document.querySelectorAll('[data-install-button]').forEach((button) => {
    button.addEventListener('click', () => {
      const mode = updateInstallPromptUi();
      if (mode === 'ios-fallback') {
        trackInstallEvent('installctaclicked', { source: 'topbar', mode });
        openInstallInstructions('topbar');
        return;
      }

      if (mode === 'prompt') {
        void handleInstallCallToAction('topbar');
        return;
      }

      showToast(t('install.promptFallback'));
    });
  });

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    updateInstallPromptState({ installedAt: null });
    scheduleInstallPrompt();
    updateInstallPromptUi();
  });

  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null;
    updateInstallPromptState({
      dismissedAt: null,
      installedAt: new Date().toISOString(),
    });
    trackInstallEvent('installsuccess', { mode: 'pwa' });
    hideInstallPromptBanner();
    closeInstallInstructions();
    updateInstallPromptUi();
    showToast(t('install.installed'));
  });

  window.addEventListener('food-reader:localechange', () => {
    updateInstallPromptUi();
  });

  const standaloneQuery = window.matchMedia?.('(display-mode: standalone)');
  standaloneQuery?.addEventListener?.('change', () => {
    updateInstallPromptUi();
  });

  scheduleInstallPrompt();
  updateInstallPromptUi();
}

export function showToast(message) {
  let toast = document.getElementById('appToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'appToast';
    toast.className = 'app-toast';
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.classList.add('visible');
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => {
    toast.classList.remove('visible');
  }, 3200);
}

showToast.timeoutId = null;

export async function setupPage({ requiresAuth = true } = {}) {
  setupLanguageControls();
  applyTranslations();
  setActiveNavLink();
  setupInstallPrompt();
  await registerServiceWorker();

  const logoutButtons = document.querySelectorAll('[data-logout]');
  logoutButtons.forEach((button) => button.addEventListener('click', logout));

  if (!requiresAuth) {
    return null;
  }

  if (!isAuthenticated()) {
    window.location.href = 'login.html';
    return null;
  }

  const user = await fetchCurrentUser();
  setCurrentUserContext(user);
  const greeting = document.querySelector('[data-user-greeting]');
  if (greeting && user) {
    greeting.textContent = user.name;
  }
  applyTranslations();
  return user;
}
