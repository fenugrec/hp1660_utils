/* ###
 * IP: GHIDRA
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *      http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
//This script counts the references to existing strings.
//@category Analysis
// sauce https://nstarke.github.io/ghidra/binary/address-offset/2021/06/06/bruteforcing-ghidra-file-offsets.html

import java.util.*;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import ghidra.program.util.DefinedDataIterator;
import ghidra.program.model.listing.Data;

public class CountReferencedStrings extends GhidraScript {

	@Override
	public void run() throws Exception {

		monitor.setMessage("Finding Strings with References");
		int referencedCount = 0;
		int totalCount = 0;
		for (Data nextData: DefinedDataIterator.definedStrings(currentProgram) ) {
			Address strAddr = nextData.getMinAddress();
			int refCount = currentProgram.getReferenceManager().getReferenceCountTo(strAddr);
			totalCount++;
			if (  refCount > 0 ) {
				referencedCount++;
			}
		}

		println("Number of referenced strings found: " + referencedCount);
		println("Total number of strings found: " + totalCount);
	}
}
