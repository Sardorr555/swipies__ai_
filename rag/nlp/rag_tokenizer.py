#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

try:
    import infinity.rag_tokenizer
    _BaseRagTokenizer = infinity.rag_tokenizer.RagTokenizer
    _is_chinese_fn = infinity.rag_tokenizer.is_chinese
    _is_number_fn = infinity.rag_tokenizer.is_number
    _is_alphabet_fn = infinity.rag_tokenizer.is_alphabet
    _naive_qie_fn = infinity.rag_tokenizer.naive_qie
except ImportError:
    class _BaseRagTokenizer:
        def tokenize(self, line: str) -> str:
            return line
        def fine_grained_tokenize(self, tks: str) -> str:
            return tks
        def tag(self, line: str) -> list:
            return []
        def freq(self, word: str) -> int:
            return 1
        def _tradi2simp(self, txt: str) -> str:
            return txt
        def _strQ2B(self, txt: str) -> str:
            return txt

    def _is_chinese_fn(s):
        return any('\u4e00' <= c <= '\u9fff' for c in str(s))

    def _is_number_fn(s):
        return str(s).isdigit()

    def _is_alphabet_fn(s):
        return str(s).isalpha()

    def _naive_qie_fn(txt):
        return [txt]

class RagTokenizer(_BaseRagTokenizer):

    def tokenize(self, line: str) -> str:
        from common import settings # moved from the top of the file to avoid circular import
        if settings.DOC_ENGINE_INFINITY:
            return line
        else:
            return super().tokenize(line)

    def fine_grained_tokenize(self, tks: str) -> str:
        from common import settings # moved from the top of the file to avoid circular import
        if settings.DOC_ENGINE_INFINITY:
            return tks
        else:
            return super().fine_grained_tokenize(tks)


def is_chinese(s):
    return _is_chinese_fn(s)


def is_number(s):
    return _is_number_fn(s)


def is_alphabet(s):
    return _is_alphabet_fn(s)


def naive_qie(txt):
    return _naive_qie_fn(txt)


tokenizer = RagTokenizer()
tokenize = tokenizer.tokenize
fine_grained_tokenize = tokenizer.fine_grained_tokenize
tag = tokenizer.tag
freq = getattr(tokenizer, "freq", lambda w: 1)
tradi2simp = getattr(tokenizer, "_tradi2simp", lambda t: t)
strQ2B = getattr(tokenizer, "_strQ2B", lambda t: t)
