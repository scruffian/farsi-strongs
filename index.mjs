import { promises as fs, constants, link } from 'fs';
// import natural from 'natural';
import translate from 'extended-google-translate-api';
import {exit } from 'process';
//import WordNet from 'natural/lib/natural/wordnet/wordnet';
// import * as use from '@tensorflow-models/universal-sentence-encoder';
// import child_process from 'child_process';
// import {PythonShell} from 'python-shell';

// Imports the Google Cloud client library
/* import { v2 } from '@google-cloud/translate';
const { Translate } = v2; */

// Creates a client
/* const translate = new Translate({
    projectId: 'cedar-hawk-340415', //eg my-proj-0o0o0o0o'
    keyFilename: 'cedar-hawk-340415-c7ae4e5b7fe4.json' //eg my-proj-0fwewexyz.json
}); */

(async function start() {
	let args = process.argv.slice(2);
	let book = args?.[0];

	if ( ! book ) {
		console.log( 'Please specify a book' );
		return;
	}

	const nmv = await fs.readFile( 'NMV.json' );
	const JsonNMV = JSON.parse( nmv );
	const NMVBooks = JsonNMV.books;
	// const verse = NMVBooks['Genesis'][0][0];
	// const book = 'Genesis'
	if (await checkFileExists('NMV_translations_'+book+'.json')) {
		const existingOutputJSON = await fs.readFile('NMV_translations_'+book+'.json');
		var outjson = JSON.parse(existingOutputJSON);
		var lastWrittenChapterIndex = outjson.books[book].length - 1;
		var lastWrittenVerseIndex = outjson.books[book][lastWrittenChapterIndex].length - 1;
	}
	else {
		var outjson = {books:{}};
		outjson.books[book]=[];
		var lastWrittenChapterIndex = -1;
		var lastWrittenVerseIndex = -1;
	};

	for (const [chapterIndex, chapter] of NMVBooks[ book ].entries()) {
		if (
			(chapterIndex > lastWrittenChapterIndex) || 
			(chapterIndex == lastWrittenChapterIndex && lastWrittenVerseIndex < (chapter.length - 1))
		) {
			// console.log(nChapter + 1);
			if (chapterIndex > lastWrittenChapterIndex) {
				outjson.books[book].push([]);
				// var nVerse = 0;
			};
			for (const [verseIndex, verse] of chapter.entries()) {
				if (
					(chapterIndex > lastWrittenChapterIndex) || 
					(chapterIndex == lastWrittenChapterIndex && verseIndex > lastWrittenVerseIndex)
				 ) {
					console.log([book, chapterIndex +1, verseIndex + 1]);
					const splitVerse = verse.split(' ');
					const verseWordPromises = splitVerse.map(async faWord => {
						const wordResult = await translate(faWord, "fa", "en").then(res => {
							//console.log(res);
							const translations = [];
							if (res['translations'] instanceof Object){
								for (const wordType of Object.keys(res['translations'])) {
									for (const translationChoiceObj of res['translations'][wordType]){
										translations.push(translationChoiceObj);
									};
								};
							}
							else if (res['translations'] instanceof Array) {
								for (const translationChoiceArr of res['translations']){
									translations.push(translationChoiceArr);
								};
							};
							return [faWord, translations];
						});
						
						return wordResult;
					});

					try {
						const verseResult = await Promise.all(verseWordPromises)
						// console.log(verseResult);
						outjson.books[book][chapterIndex].push(verseResult);
					} catch (error) {
						if (error['message'] == 'HTTPError') {
							console.log('API call limit reached');
							await fs.writeFile('NMV_translations_'+book+'.json', JSON.stringify(outjson));
							exit(0);
						};
					};
				};
			};
		};
	};
		
	await fs.writeFile("NMV_translations_"+book+".json", JSON.stringify(outjson));
})();

async function checkFileExists(file) {
	try {
		const result = await fs.access(file).then(() => true);

		return result;
	} catch {
		const result = false;

		return result;
	};
  };
	// const wordnet = new natural.WordNet()
	// const esv = await fs.readFile( 'ESV.json', 'utf8' );
	// const JsonESV = JSON.parse( esv );
	// const ESVBooks = JsonESV.books;
	/*Object.keys( ESVBooks ).forEach( book => {
		ESVBooks[ book ].forEach( chapter => {
			chapter.forEach( verse => {
				verse.forEach( word => {
					console.log( word );
				} );
			} );
		})
	})*/

				/* const similarities = []
				for (const englishWord of ESVBooks['Genesis'][0][0]) {
					if ( englishWord[1] ) {
						for (const translatedWord of translations) {
							const options = {
								mode: 'text',
								pythonPath: '...\\python.exe',
								pythonOptions: ['-u'], // get print results in real-time
								scriptPath: '...\\farsi-strongs',
								args: [translatedWord, englishWord[0]]
							};

							PythonShell.run('wupsimilarity.py', options, function (err, results) {
								if (err) throw err;
								// results is an array consisting of messages collected during execution
								similarities.push(
									{
										similarity: results,
										translation:translatedWord,
										ESVword:englishWord[0],
										strongs:englishWord[1]
									}
								);
							});
							if (translatedWord == englishWord[0]) {
								console.log([faWord, translatedWord, englishWord])
							}
						};

					};
				}; */

	// const faWord = verse[1]



			// const faWordTranslations = { faWord: translations}

			/* translations.forEach(translatedWord => {
				wordnet.lookup(translatedWord, function(details) {
					details.forEach(function(detail) {
						console.log([res['word'], translatedWord, detail.synonyms])
					});
				});

			}); */


	/* translatedVerse.forEach( translatedWord => {
		ESVBooks['Genesis'][0][0].forEach( englishWord => {
			if ( englishWord[1] ) {

				const esvWord = natural.PorterStemmer.stem(englishWord[0]);
				if (' ' in translatedWord) {
					const farsiWord = natural.PorterStemmer.attach(translatedWord.tokenizeAndStem());
					//console.log(tokenizer.tokenize("my dog hasn't any fleas."));
					//const farsiWordArr = tokenizer.tokenize(translatedWord).stem();
				}
				else {
					const farsiWord = natural.PorterStemmer.stem(translatedWord);
				}
				//console.log( esvWord, farsiWord );

				//console.log("I can see that we are going to be friends".tokenizeAndStem())
				//console.log( esvWord.tokenizeAndStem() );
				if ( esvWord == farsiWord ) {
					console.log( englishWord.slice(0,2)  );
				}
			}
 		} )
	} ) */

/* async function googleTranslateText( text ) {
	const target = 'en';

	// Translates the text into the target language. "text" can be a string for
	// translating a single piece of text, or an array of strings for translating
	// multiple texts.
	console.log( translate.translate );
	let [translations] = await translate.translate(text, target);
	translations = Array.isArray(translations) ? translations : [translations];

	return translations;
	translations.forEach((translation, i) => {
		console.log(`${text[i]} => (${target}) ${translation}`);
	});
} */

/* function semanticSimilarity (string1, string2) {
	use.load().then(model => {
		const sentences = [
			string1,
			string2
		];
		model.embed(sentences).then(embeddings => {
			const a = embeddings[0]
			const b = embeddings[1]
			const magnitudeA = Math.sqrt(this.dot(a, a));
			const magnitudeB = Math.sqrt(this.dot(b, b));
			if (magnitudeA && magnitudeB){
				return this.dot(a, b) / (magnitudeA * magnitudeB);
			}
			else {
				return NaN
			};
		});
	});


} */
