import {parseRange} from "./download-worker.js";
import assert from "node:assert/strict";
assert.deepEqual(parseRange(null,100),[0,99]);
assert.deepEqual(parseRange("bytes=99-",100),[99,99]);
assert.deepEqual(parseRange("bytes=-32",100),[68,99]);
assert.deepEqual(parseRange("bytes=10-999",100),[10,99]);
for(const value of ["bytes=100-","bytes=-0","bytes=8-7","bytes=1-2,3-4","bytes=-","x=0-3"])assert.throws(()=>parseRange(value,100));
console.log("Range validation passed");
