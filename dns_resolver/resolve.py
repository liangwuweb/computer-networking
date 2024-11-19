"""
resolve.py: a recursive resolver built using dnspython
"""

from multiprocessing import Process, Queue
import time
import argparse
import random
import dns.message
import dns.name
import dns.query
import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.rdtypes
import dns.resolver


FORMATS = (
    ("CNAME", "{alias} is an alias for {name}"),
    ("A", "{name} has address {address}"),
    ("AAAA", "{name} has IPv6 address {address}"),
    ("MX", "{name} mail is handled by {preference} {exchange}"),
)

# current as of 19 October 2020
ROOT_SERVERS = (
    "198.41.0.4",
    "199.9.14.201",
    "192.33.4.12",
    "199.7.91.13",
    "192.203.230.10",
    "192.5.5.241",
    "192.112.36.4",
    "198.97.190.53",
    "192.36.148.17",
    "192.58.128.30",
    "193.0.14.129",
    "199.7.83.42",
    "202.12.27.33",
)


def collect_results(name: str) -> dict:
    """
    This function parses final answers into the proper data structure that
    print_results requires. The main work is done within the `lookup` function.
    """
    full_response = {}
    target_name = dns.name.from_text(name)
    try:
        # lookup CNAME
        response = lookup(target_name, dns.rdatatype.CNAME)
        cnames = []
        for answers in response.answer:
            for answer in answers:
                cnames.append({"name": answer, "alias": name})
        # lookup A
        response = lookup(target_name, dns.rdatatype.A)
        arecords = []
        for answers in response.answer:
            a_name = answers.name
            for answer in answers:
                if answer.rdtype == 1:  # A record
                    arecords.append({"name": a_name, "address": str(answer)})
        # lookup AAAA
        response = lookup(target_name, dns.rdatatype.AAAA)
        aaaarecords = []
        for answers in response.answer:
            aaaa_name = answers.name
            for answer in answers:
                if answer.rdtype == 28:  # AAAA record
                    aaaarecords.append({"name": aaaa_name,
                                        "address": str(answer)})
        # lookup MX
        response = lookup(target_name, dns.rdatatype.MX)
        mxrecords = []
        for answers in response.answer:
            mx_name = answers.name
            for answer in answers:
                if answer.rdtype == 15:  # MX record
                    mxrecords.append(
                        {
                            "name": mx_name,
                            "preference": answer.preference,
                            "exchange": str(answer.exchange),
                        }
                    )

        full_response["CNAME"] = cnames
        full_response["A"] = arecords
        full_response["AAAA"] = aaaarecords
        full_response["MX"] = mxrecords

    except dns.resolver.Timeout:
        print("Request timeout")
    except Exception:
        print("Request timeout")

    return full_response


def pick_random() -> str:
    """ "
    pick a random root server
    """
    return random.choice(ROOT_SERVERS)


# Global Cache
cache = {}


def lookup_helper(
    target_name: dns.name.Name, qtype: dns.rdata.Rdata, server: str
) -> dns.message.Message:
    """ "
    helper method asks the root servers
    and recurses to find the proper answer.
    """

    labels = target_name.labels
    for i in range(len(labels)):
        subdomain = dns.name.Name(labels[i:])
        cache_key = (str(subdomain), qtype)
        if cache_key in cache:
            #print(f"Cache hit for {cache_key}")
            return cache[cache_key]

    outbound_query = dns.message.make_query(target_name, qtype)
    try:
        response = dns.query.udp(outbound_query, server, 3)
        if response.answer:
            # Cache the answer for the current target_name (full domain)
            cache_key = (str(target_name), qtype)
            cache[cache_key] = response
            # test caching
            # print(f"Added to cache: {cache_key}")

            # Cache intermediate results for each label level
            for i in range(len(labels)):
                subdomain = dns.name.Name(labels[i:])
                subdomain_key = (str(subdomain), qtype)
                if subdomain_key not in cache:
                    cache[subdomain_key] = response
                    # test caching
                    # print(f"Added intermediate result
                    # to cache: {subdomain_key}")

            # handle CNAME in record
            for answer_section in response.answer:
                for record in answer_section:
                    if record.rdtype == dns.rdatatype.CNAME:
                        canonical_name = str(record.target)
                        return lookup_helper(
                            dns.name.from_text(canonical_name),
                            dns.rdatatype.A,
                            pick_random(),
                        )
            return response
        elif response.additional:
            for additional in response.additional:
                for item in additional:
                    if item.rdtype == dns.rdatatype.A:
                        return lookup_helper(target_name, qtype, str(item))
        # handle unglued nameserver
        elif response.authority:
            for authority in response.authority:
                for ns_record in authority:
                    if ns_record.rdtype == dns.rdatatype.NS:
                        ns_name = str(ns_record.target)
                        # resolve ip address
                        ns_response = lookup_helper(
                            dns.name.from_text(ns_name),
                            dns.rdatatype.A, pick_random()
                        )
                        if ns_response and ns_response.answer:
                            next_server_ip = str(ns_response.answer[0][0])
                            return lookup_helper(target_name, qtype, next_server_ip)
    except dns.exception.Timeout:
        print("Error querying server from inner")
        return None

    return response


def process_lookup(
    target_name: dns.name.Name, qtype: dns.rdata.Rdata, result_queue: Queue
):
    """
    A wrapper function to run the lookup_helper in a separate process
    """
    try:
        response = lookup_helper(target_name, qtype, pick_random())
        result_queue.put(response)  # Put the result in the queue
    except dns.exception.Timeout:
        result_queue.put(None)  # In case of timeout


def lookup(target_name: dns.name.Name, qtype: dns.rdata.Rdata) -> dns.message.Message:
    """
    This function uses a recursive resolver to find the relevant answer to the
    query.
    """

    # Check if the result is already in the cache
    cache_key = (str(target_name), qtype)
    if cache_key in cache:
        # test caching
        # print(f"Cache hit for {cache_key}")
        return cache[cache_key]  # Return cached result if found

    start = time.time()
    result = Queue()  # Create a Queue to get the result from the process
    p = Process(
        target=process_lookup, args=(target_name, qtype, result), name="Process_lookup"
    )

    p.start()  # Start the process

    p.join(timeout=3)  # Wait for the process to complete with a timeout of 3 seconds
    end = time.time()
    elapsed_time = end - start
    if p.is_alive():
        p.terminate()  # Terminate the process if it's still running
        p.join()  # Ensure the process is terminated
        print(f"Time out: {elapsed_time}")
        return None
    else:
        if not result.empty():
            response = result.get()
            # Store the response in the cache before returning it
            cache[cache_key] = response
            return response
        else:
            return None


def print_results(results: dict) -> None:
    """
    take the results of a `lookup` and print them to the screen like the host
    program would.
    """

    for rtype, fmt_str in FORMATS:
        for result in results.get(rtype, []):
            print(fmt_str.format(**result))


def caching(my_list: list) -> list:
    """
    simple caching system, so that exact duplicate lookups for
    the same domain do not result in additional queries.
    """
    unique = []
    seen = set()
    for item in my_list:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def main():
    """
    if run from the command line, take args and call
    printresults(lookup(hostname))
    """
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("name", nargs="+", help="DNS name(s) to look up")
    argument_parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    program_args = argument_parser.parse_args()

    # remove duplicates from the list
    domain_list = caching(program_args.name)

    for a_domain_name in domain_list:
        print_results(collect_results(a_domain_name))


if __name__ == "__main__":
    main()
