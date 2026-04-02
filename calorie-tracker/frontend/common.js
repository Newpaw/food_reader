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
    'button.logout': 'Log out',
    'button.takePhoto': 'Take photo now',
    'button.useSavedPhoto': 'Use saved photo',
    'button.choosePhoto': 'Choose photo',
    'button.analyzePhoto': 'Analyze meal photo',
    'button.analyzeText': 'Analyze meal text',
    'button.applyRange': 'Apply range',
    'button.refreshMetrics': 'Refresh metrics',
    'button.saveProfile': 'Save profile',
    'button.resetForm': 'Reset form',
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
    'button.startVoice': 'Start voice input',
    'button.stopVoice': 'Stop listening',
    'button.syncQueue': 'Sync queue',
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
    'login.heroEyebrow': 'Built for real phones',
    'login.heroTitle': 'Track meals fast, then install the app and keep it on your home screen.',
    'login.heroBody': 'The interface is tuned for quick one-handed logging, clear review states, and clean historical reporting.',
    'login.welcomeBack': 'Welcome back',
    'login.signInHeading': 'Sign in',
    'login.newAccount': 'New account',
    'login.createAccess': 'Create access',
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
    'home.mobileCameraHint': 'Open the camera directly on your phone, then review the estimate before saving.',
    'home.uploadHint': 'Use the camera for a quick capture or choose a saved image.',
    'home.analysisLoadingTitle': 'Analyzing your meal',
    'home.analysisLoadingBody': 'This can take a few seconds.',
    'home.voiceHint': 'Dictate a meal and then review the estimate before saving.',
    'home.recentEyebrow': 'Keep moving',
    'home.recentHeading': 'Recent meals',
    'home.reviewEyebrow': 'Review',
    'home.reviewHeading': 'Adjust the nutrition draft',
    'home.latestEntry': 'Latest entry',
    'home.correctionHeading': 'Correct the AI identification',
    'home.correctionPlaceholder': 'Example: this was grilled pork, not chicken',
    'home.templatesEmpty': 'Save a reviewed meal and it will appear here for one-tap logging.',
    'home.queueEmpty': 'Nothing is waiting to sync.',
    'home.queueHeading': 'Offline capture queue',
    'home.queueReady': 'Everything is synced.',
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
    'home.textRequired': 'Describe the meal before submitting.',
    'home.photoAnalyzing': 'Analyzing your meal photo...',
    'home.textAnalyzing': 'Analyzing your meal description...',
    'home.mealAdded': 'Meal added. Review the estimate below.',
    'home.savingAdjustments': 'Saving adjustments...',
    'home.mealUpdated': 'Meal updated.',
    'home.mealDeleted': 'Meal deleted.',
    'home.deleteConfirm': 'Delete this meal permanently?',
    'home.resetDone': 'Changes reset.',
    'home.correctionRequired': 'Add a correction before re-running the analysis.',
    'home.reanalyzing': 'Reanalyzing meal...',
    'home.reanalysisUpdated': 'AI analysis updated.',
    'home.noMeals': 'No meals yet. Add one to get started.',
    'history.heroEyebrow': 'History',
    'history.heroTitle': 'Review the full log, grouped in a way that still works on a phone.',
    'history.heroBody': 'Filter a date range, spot outliers quickly, and adjust entries without leaving the history screen.',
    'history.filterEyebrow': 'Range',
    'history.filterHeading': 'Filter history',
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
    'profile.heroEyebrow': 'Profile',
    'profile.heroTitle': 'Store the context that makes the dashboard useful.',
    'profile.heroBody': 'Save baseline body data, activity level, and optional custom targets so the app can compare intake against something real.',
    'profile.inputsEyebrow': 'Inputs',
    'profile.inputsHeading': 'Personal settings',
    'profile.outputsEyebrow': 'Outputs',
    'profile.outputsHeading': 'Current targets',
    'profile.overridesEyebrow': 'Optional overrides',
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
    'button.logout': 'Odhlásit',
    'button.takePhoto': 'Vyfotit hned',
    'button.useSavedPhoto': 'Použít uloženou fotku',
    'button.choosePhoto': 'Vybrat fotku',
    'button.analyzePhoto': 'Analyzovat fotku jídla',
    'button.analyzeText': 'Analyzovat text jídla',
    'button.applyRange': 'Použít rozsah',
    'button.refreshMetrics': 'Obnovit přehled',
    'button.saveProfile': 'Uložit profil',
    'button.resetForm': 'Obnovit formulář',
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
    'button.startVoice': 'Spustit diktování',
    'button.stopVoice': 'Zastavit poslech',
    'button.syncQueue': 'Synchronizovat frontu',
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
    'login.heroEyebrow': 'Navrženo pro skutečné telefony',
    'login.heroTitle': 'Zapisujte jídla rychle, nainstalujte aplikaci a mějte ji na ploše.',
    'login.heroBody': 'Rozhraní je vyladěné pro rychlé ovládání jednou rukou, jasnou kontrolu výsledků a čistou historii.',
    'login.welcomeBack': 'Vítejte zpět',
    'login.signInHeading': 'Přihlášení',
    'login.newAccount': 'Nový účet',
    'login.createAccess': 'Vytvořit přístup',
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
    'home.mobileCameraHint': 'Otevřete rovnou fotoaparát v telefonu a před uložením výsledek zkontrolujte.',
    'home.uploadHint': 'Použijte fotoaparát pro rychlé zachycení nebo vyberte uložený obrázek.',
    'home.analysisLoadingTitle': 'Analyzuji vaše jídlo',
    'home.analysisLoadingBody': 'To může trvat několik sekund.',
    'home.voiceHint': 'Nadiktujte jídlo a potom odhad zkontrolujte před uložením.',
    'home.recentEyebrow': 'Pokračujte',
    'home.recentHeading': 'Poslední jídla',
    'home.reviewEyebrow': 'Kontrola',
    'home.reviewHeading': 'Upravte návrh nutričních hodnot',
    'home.latestEntry': 'Poslední záznam',
    'home.correctionHeading': 'Opravte AI rozpoznání',
    'home.correctionPlaceholder': 'Například: bylo to grilované vepřové, ne kuře',
    'home.templatesEmpty': 'Uložte zkontrolované jídlo nebo produkt a objeví se zde pro jedno klepnutí.',
    'home.queueEmpty': 'Nic nečeká na synchronizaci.',
    'home.queueHeading': 'Offline fronta záznamů',
    'home.queueReady': 'Všechno je synchronizované.',
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
    'home.textRequired': 'Nejdřív popište jídlo.',
    'home.photoAnalyzing': 'Analyzuji fotku jídla...',
    'home.textAnalyzing': 'Analyzuji popis jídla...',
    'home.mealAdded': 'Jídlo bylo přidáno. Zkontrolujte odhad níže.',
    'home.savingAdjustments': 'Ukládám úpravy...',
    'home.mealUpdated': 'Jídlo bylo aktualizováno.',
    'home.mealDeleted': 'Jídlo bylo smazáno.',
    'home.deleteConfirm': 'Smazat toto jídlo natrvalo?',
    'home.resetDone': 'Změny byly vráceny.',
    'home.correctionRequired': 'Před opětovnou analýzou přidejte opravu.',
    'home.reanalyzing': 'Provádím novou analýzu...',
    'home.reanalysisUpdated': 'AI analýza byla aktualizována.',
    'home.noMeals': 'Zatím tu nejsou žádná jídla. Přidejte první.',
    'history.heroEyebrow': 'Historie',
    'history.heroTitle': 'Projděte celý deník v rozložení, které funguje i na telefonu.',
    'history.heroBody': 'Filtrujte datumy, rychle najděte odlehlé záznamy a upravujte je bez opuštění historie.',
    'history.filterEyebrow': 'Rozsah',
    'history.filterHeading': 'Filtrovat historii',
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
    'profile.heroEyebrow': 'Profil',
    'profile.heroTitle': 'Uložte kontext, který dělá dashboard užitečným.',
    'profile.heroBody': 'Uložte základní tělesná data, aktivitu a případné vlastní cíle, aby aplikace porovnávala příjem s realitou.',
    'profile.inputsEyebrow': 'Vstupy',
    'profile.inputsHeading': 'Osobní nastavení',
    'profile.outputsEyebrow': 'Výstupy',
    'profile.outputsHeading': 'Aktuální cíle',
    'profile.overridesEyebrow': 'Volitelné přepisy',
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
    /^reanalysis with corrections:\s*/i,
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

let deferredInstallPrompt = null;

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
  const from = fromDate ? new Date(`${fromDate}T00:00:00`) : null;
  const to = toDate ? new Date(`${toDate}T00:00:00`) : null;

  if (to) {
    to.setDate(to.getDate() + 1);
  }

  return {
    from: from ? from.toISOString() : null,
    to: to ? to.toISOString() : null,
  };
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

export async function registerServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }

  try {
    await navigator.serviceWorker.register('/service-worker.js?v=20260402-3');
  } catch (error) {
    console.error('Service worker registration failed:', error);
  }
}

export function setupInstallPrompt() {
  const installButton = document.querySelector('[data-install-button]');
  if (!installButton) {
    return;
  }

  installButton.addEventListener('click', async () => {
    if (!deferredInstallPrompt) {
      showToast(t('install.promptFallback'));
      return;
    }

    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
    installButton.hidden = true;
  });

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    installButton.hidden = false;
  });

  window.addEventListener('appinstalled', () => {
    installButton.hidden = true;
    deferredInstallPrompt = null;
  });
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
