import { promises as fs, constants, link } from 'fs';
import translate from 'google-translate-extended-api';
import {exit } from 'process';


(async function start() {

	const nmv = await fs.readFile( 'keyed-words.json' );
	var keyed_words = JSON.parse( nmv );
	keyed_words = Object.keys(keyed_words);
	keyed_words = keyed_words.slice(15);

	if (await checkFileExists('transformations/keyed_words_translations.json')) {
		const existingOutputJSON = await fs.readFile('transformations/keyed_words_translations.json');
		var outjson = JSON.parse(existingOutputJSON);
		keyed_words = keyed_words.slice(outjson.length);
	}
	else {
		var outjson = {};
	};

	for (const [idx, faword] of keyed_words.entries()) {
		console.log(faword);
		try {
            
            const wordResult = await translate(faword, "fa", "en");
            outjson[faword] = wordResult;
        } catch (error) {
            if (error['message'] == 'HTTPError') {
                console.log('API call limit reached');
                await fs.writeFile('transformations/keyed_words_translations.json', JSON.stringify(outjson));
                exit(0);
            }
			else {
				console.log(error)
			};
        };
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