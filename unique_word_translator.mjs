import { promises as fs, constants, link } from 'fs';
import translate from 'google-translate-extended-api';
import { exit } from 'process';

(async function start() {
	// Read list of unique farsi words from keys of input file
	const nmv = await fs.readFile( 'keyed-words.json' );
	var keyed_words = JSON.parse( nmv );
	keyed_words = Object.keys(keyed_words);

	// Set chunk size for async api calls
	const chunksize = 20

	// Remove punctuation at start of words array
	keyed_words = keyed_words.slice(15);
	const iterations = Math.ceil(keyed_words.length / chunksize);

	// Pick up from where last run left off if previously run
	if (await checkFileExists('transformations/keyed_words_translations.json')) {
		const existingOutputJSON = await fs.readFile('transformations/keyed_words_translations.json');
		var outjson = JSON.parse(existingOutputJSON);
		keyed_words = keyed_words.slice(Object.keys(outjson).length+1);
	}
	else {
		var outjson = {};
	};

	// Iterate through chunks of unique words and pass to translate api
	for (var i=0; i < iterations; i++){
		var chunk = keyed_words.splice(0,chunksize);
		var chunkPromises = chunk.map(async faWord => {
			var wordResult = await translate(faWord, "fa", "en");
			return wordResult;
		});
		// Append translation results to outjson
		try {
            var results = await Promise.all(chunkPromises);
			results.forEach(obj => {
				outjson[obj['word']] = obj;
			});
        } 

		// Write outjson with appended results so far to file on error
		catch (error) {
            if (error['message'] == 'HTTPError') {
                console.log('API call limit reached');
                await fs.writeFile('transformations/keyed_words_translations.json', JSON.stringify(outjson));
                exit(0);
            }
			else {
				console.log(error)
				await fs.writeFile('transformations/keyed_words_translations.json', JSON.stringify(outjson));
				exit(0);
			};
        };
		var progress = (i/iterations)*100;
		progress = progress.toFixed(2);
		console.clear();
		console.log('\r' + progress + "% complete");
    };	
	await fs.writeFile("transformations/keyed_words_translations.json", JSON.stringify(outjson));
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