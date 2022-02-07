import { promises as fs, constants, link } from 'fs';
import natural from 'natural';

// Imports the Google Cloud client library
import { v2 } from '@google-cloud/translate';
const { Translate } = v2;

// Creates a client
const translate = new Translate({
    projectId: 'cedar-hawk-340415', //eg my-proj-0o0o0o0o'
    keyFilename: 'cedar-hawk-340415-c7ae4e5b7fe4.json' //eg my-proj-0fwewexyz.json
});

(async function start() {
	const esv = await fs.readFile( 'ESV.json', 'utf8' );
	const JsonESV = JSON.parse( esv );
	const ESVBooks = JsonESV.books;
	/*Object.keys( ESVBooks ).forEach( book => {
		ESVBooks[ book ].forEach( chapter => {
			chapter.forEach( verse => {
				verse.forEach( word => {
					console.log( word );
				} );
			} );
		})
	})*/

	const nmv = await fs.readFile( 'NMV.json' );
	const JsonNMV = JSON.parse( nmv );
	const NMVBooks = JsonNMV.books;
	const verse = NMVBooks['Genesis'][0][0].split( ' ' );

	/*Object.keys( NMVBooks ).forEach( book => {
		NMVBooks[ book ].forEach( chapter => {
			chapter.forEach( verse => {
				verse.split( ' ' ).forEach( word => {
					console.log( word );
				} );
			} );
		})
	});*/
	natural.PorterStemmer.attach();
	const translatedVerse = await googleTranslateText( verse );
	translatedVerse.forEach( translatedWord => {
		ESVBooks['Genesis'][0][0].forEach( englishWord => {
			if ( englishWord[1] ) {
				const esvWord = englishWord[0].toLowerCase();
				const farsiWord = translatedWord.toLowerCase();
				//console.log( esvWord, farsiWord );

				//console.log("I can see that we are going to be friends".tokenizeAndStem())
				console.log( esvWord.tokenizeAndStem() );
				if ( esvWord.indexOf( farsiWord ) > -1 ) {
					console.log( englishWord[0] );
				}
			}
 		} )
	} )



})();


async function googleTranslateText( text ) {
	const target = 'en';

	// Translates the text into the target language. "text" can be a string for
	// translating a single piece of text, or an array of strings for translating
	// multiple texts.
	console.log( translate.translate );
	let [translations] = await translate.translate(text, target);
	translations = Array.isArray(translations) ? translations : [translations];

	return translations;
	/*translations.forEach((translation, i) => {
		console.log(`${text[i]} => (${target}) ${translation}`);
	});*/
}
