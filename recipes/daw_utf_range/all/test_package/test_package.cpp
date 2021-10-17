#include <iostream>
#include "daw/utf_range/daw_utf_range.h"

int main() {
    auto constexpr const rng = daw::range::create_char_range(u8"あいうえお");

    std::cout << rng.size() << std::endl;

    return 0;
}
