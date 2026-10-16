/**
 * 質問フォーム自動生成 / Question Form generator  (Google Apps Script)
 * ---------------------------------------------------------------------------
 * 使い方 / How to use:
 *   1. https://script.google.com を開き「新しいプロジェクト」を作成
 *   2. このコードを全文貼り付けて保存
 *   3. 上部の関数選択で buildForm を選び「実行」（初回のみ権限承認のダイアログが出る → 許可）
 *   4. 実行ログ（表示 > 実行ログ / Ctrl+Enter）に出る 2 本の URL を開く
 *        - 編集用URL : フォームを手で微調整する画面
 *        - 回答用URL : 配布する公開フォーム
 *
 * 生成されるフォーム構成 / Structure:
 *   [ページ1] 区分(日本人学生/留学生)   ← この回答で分岐
 *       ├─ 「日本人学生」を選択 → [ページ2] 日本語ラベルのセクション
 *       └─ 「留学生」を選択     → [ページ3] 日英併記ラベルのセクション
 *   どちらのセクションも必須項目: 学籍番号 / 学科 / 名前 / メールアドレス / 質問
 * ---------------------------------------------------------------------------
 */

// ===== 設定（ここだけ編集すれば中身を変えられる）/ CONFIG =====================
var CONFIG = {
  title: '質問フォーム / Question Form',
  description: '質問を受け付けるフォームです。\nA form to receive your questions.',

  // true にすると回答者の Google アカウントのメールを自動収集する。
  //   ※ 注意: 下に「メールアドレス」手入力欄もあるため、true にすると二重に聞くことになる。
  //     自動収集を使うなら addStandardFields 内のメール欄を削るか、どちらか一方に統一する。
  collectEmailAutomatically: false,

  // 日本人学生セクションも日英併記にしたい場合は true（既定は日本語のみ）
  japaneseSectionBilingual: false,

  // 学籍番号の形式チェック（正規表現）。空文字 '' にするとチェックなし。
  //   例: S00X0000 形式（英字1・数字2・英字1・数字4）→ '^[A-Za-z]\\d{2}[A-Za-z]\\d{4}$'
  studentIdPattern: '',

  // 学科の選択肢（日本人セクション用：日本語）。例なので、自分の大学の学科に差し替える
  departmentsJa: [
    '機械工学科', '電気電子工学科', '情報工学科', '化学科',
    '建築学科', '経営学科', 'その他'
  ],
  // 学科の選択肢（留学生セクション用：日英併記）。上と同じ順にそろえる
  departmentsBi: [
    '機械工学科 / Mechanical Engineering',
    '電気電子工学科 / Electrical and Electronic Engineering',
    '情報工学科 / Computer Science',
    '化学科 / Chemistry',
    '建築学科 / Architecture',
    '経営学科 / Business Administration',
    'その他 / Other'
  ]
};
// ===========================================================================

// 各セクションの項目ラベル。左=日本語のみ、右=日英併記。
var LABELS_JA = {
  studentId: '学籍番号',
  department: '学科',
  name: '名前',
  email: 'メールアドレス',
  question: '質問',
  studentIdError: '学籍番号の形式が正しくありません。',
  emailError: '正しいメールアドレスを入力してください。'
};
var LABELS_BI = {
  studentId: '学籍番号 / Student ID',
  department: '学科 / Department',
  name: '名前 / Name',
  email: 'メールアドレス / Email address',
  question: '質問 / Question',
  studentIdError: '学籍番号の形式が正しくありません。/ Invalid student ID format.',
  emailError: '正しいメールアドレスを入力してください。/ Please enter a valid email address.'
};

function buildForm() {
  var form = FormApp.create(CONFIG.title);
  form.setDescription(CONFIG.description);
  form.setProgressBar(true);
  form.setCollectEmail(CONFIG.collectEmailAutomatically);

  // --- ページ1: 冒頭の共通質問 -------------------------------------------
  // 区分選択（この回答で分岐する）。選択肢は後でセクション生成後に設定する。
  //   ※「言語 / Language」質問は付けない（表示言語は区分で決まるため不要）。
  var categoryItem = form.addMultipleChoiceItem()
    .setTitle('区分 / Category')
    .setHelpText('あてはまる方を選んでください。/ Please select one.')
    .setRequired(true);

  // --- ページ2: 日本人学生用セクション -----------------------------------
  var jpSection = form.addPageBreakItem()
    .setTitle('日本人学生用')
    .setHelpText('以下の項目をすべて入力してください。');
  addStandardFields(form,
    CONFIG.japaneseSectionBilingual ? LABELS_BI : LABELS_JA,
    CONFIG.japaneseSectionBilingual ? CONFIG.departmentsBi : CONFIG.departmentsJa);

  // --- ページ3: 留学生用セクション（日英併記）----------------------------
  var intlSection = form.addPageBreakItem()
    .setTitle('留学生用 / For International Students')
    .setHelpText('すべての項目に入力してください。/ Please fill in all fields.');
  addStandardFields(form, LABELS_BI, CONFIG.departmentsBi);

  // --- 分岐の配線 --------------------------------------------------------
  // 「区分」の各選択肢を、対応するセクション(ページ)へジャンプさせる
  categoryItem.setChoices([
    categoryItem.createChoice('日本人学生 / Japanese student', jpSection),
    categoryItem.createChoice('留学生 / International student', intlSection)
  ]);

  // 日本人セクション（ページ2）を埋め終えたら、そのまま留学生セクションへ
  // 流れ落ちないよう「送信」へジャンプさせる。
  // ※ PageBreakItem.setGoToPage は「この区切りの“手前のページ”を完了した後の遷移先」を定める。
  //   intlSection の手前ページ = 日本人セクション。これで日本人は留学生欄を飛ばして送信できる。
  intlSection.setGoToPage(FormApp.PageNavigationType.SUBMIT);

  // --- （任意）回答を新規スプレッドシートに保存したい場合はコメントを外す ---
  // var ss = SpreadsheetApp.create(CONFIG.title + ' 回答');
  // form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  // --- 完了ログ ----------------------------------------------------------
  Logger.log('✅ フォームを作成しました / Form created');
  Logger.log('編集用URL (Edit): ' + form.getEditUrl());
  Logger.log('回答用URL (Live): ' + form.getPublishedUrl());
}

/**
 * 5つの必須項目（学籍番号・学科・名前・メール・質問）をフォーム末尾に追加する。
 * @param {Form} form      対象フォーム
 * @param {Object} labels  ラベル集（LABELS_JA か LABELS_BI）
 * @param {string[]} departments  学科プルダウンの選択肢
 */
function addStandardFields(form, labels, departments) {
  // 学籍番号（短文 + 任意の形式チェック）
  var idItem = form.addTextItem().setTitle(labels.studentId).setRequired(true);
  if (CONFIG.studentIdPattern) {
    idItem.setValidation(
      FormApp.createTextValidation()
        .setHelpText(labels.studentIdError)
        .requireTextMatchesPattern(CONFIG.studentIdPattern)
        .build()
    );
  }

  // 学科（プルダウン）
  form.addListItem()
    .setTitle(labels.department)
    .setChoiceValues(departments)
    .setRequired(true);

  // 名前（短文）
  form.addTextItem().setTitle(labels.name).setRequired(true);

  // メールアドレス（短文 + 形式チェック）
  form.addTextItem()
    .setTitle(labels.email)
    .setRequired(true)
    .setValidation(
      FormApp.createTextValidation()
        .setHelpText(labels.emailError)
        .requireTextIsEmail()
        .build()
    );

  // 質問（長文）
  form.addParagraphTextItem().setTitle(labels.question).setRequired(true);
}
